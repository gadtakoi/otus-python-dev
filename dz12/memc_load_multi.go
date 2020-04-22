package main

import (
	"./appsinstalled"

	"bufio"
	"compress/gzip"
	"errors"
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"

	"github.com/bradfitz/gomemcache/memcache"
	"github.com/golang/protobuf/proto"
)

type AppsInstalled struct {
	devType string
	devId   string
	lat     float64
	lon     float64
	apps    []uint32
}

type Options struct {
	logfile string
	workers int
	buffer  int
	pattern string
}

type MemcacheItem struct {
	key  string
	data []byte
}

type Result struct {
	processed int
	errors    int
}

const NORMAL_ERR_RATE = 0.01

func createMemcaches(options *Options, resultsQueue chan Result) map[string]chan *MemcacheItem {

	memcQueues := make(map[string]chan *MemcacheItem)

	deviceMemc := map[string]string{
		"idfa": idfa,
		"gaid": gaid,
		"adid": adid,
		"dvid": dvid,
	}

	for devType, memcAddr := range deviceMemc {
		memcQueues[devType] = make(chan *MemcacheItem, options.buffer)
		m := memcache.New(memcAddr)
		go MemcacheWorker(m, memcQueues[devType], resultsQueue)
	}

	return memcQueues
}

func MemcacheWorker(mc *memcache.Client, items chan *MemcacheItem, resultsQueue chan Result) {
	processed, errs := 0, 0

	for {
		task, ok := <-items
		if !ok {
			resultsQueue <- Result{processed, errs}
			log.Printf("memcache processed %d | errors %d", processed, errs)
			return
		}

		err := mc.Set(&memcache.Item{
			Key:   task.key,
			Value: task.data,
		})

		if err != nil {
			errs++
			log.Println(err)
		} else {
			processed++
		}
	}
}

func LineParser(lines chan string, memcQueues map[string]chan *MemcacheItem, resultsQueue chan Result) {
	errs := 0
	for line := range lines {
		appsInstalled, err := parseAppsInstalled(line)
		if err != nil {
			errs += 1
			continue
		}
		item, err := SerializeAppsInstalled(appsInstalled)
		if err != nil {
			errs += 1
			continue
		}
		queue, ok := memcQueues[appsInstalled.devType]
		if !ok {
			log.Println("Unknown device type:", appsInstalled.devType)
			errs += 1
			continue
		}
		queue <- item
	}
	resultsQueue <- Result{errors: errs}
}

func parseAppsInstalled(line string) (*AppsInstalled, error) {
	line = strings.Trim(line, "")
	unpacked := strings.Split(line, "\t")
	if len(unpacked) != 5 {
		return nil, errors.New("Bad line: " + line)
	}
	devType, devId, rawLat, rawLon, rawApps := unpacked[0], unpacked[1], unpacked[2], unpacked[3], unpacked[4]
	lat, err := strconv.ParseFloat(rawLat, 64)
	if err != nil {
		return nil, err
	}
	lon, err := strconv.ParseFloat(rawLon, 64)
	if err != nil {
		return nil, err
	}
	var apps []uint32
	for _, rawApp := range strings.Split(rawApps, ",") {
		if app, err := strconv.ParseUint(rawApp, 10, 32); err == nil {
			apps = append(apps, uint32(app))
		}
	}

	return &AppsInstalled{
		devType: devType,
		devId:   devId,
		lat:     lat,
		lon:     lon,
		apps:    apps,
	}, nil
}

func SerializeAppsInstalled(appsInstalled *AppsInstalled) (*MemcacheItem, error) {
	aua := &appsinstalled.UserApps{
		Lat:  proto.Float64(appsInstalled.lat),
		Lon:  proto.Float64(appsInstalled.lon),
		Apps: appsInstalled.apps,
	}
	key := fmt.Sprintf("%s:%s", appsInstalled.devType, appsInstalled.devId)
	packed, err := proto.Marshal(aua)
	if err != nil {
		return nil, err
	}
	return &MemcacheItem{key, packed}, nil
}

func fileReader(filename string, linesQueue chan string) error {
	log.Println("Processing:", filename)
	f, err := os.Open(filename)
	if err != nil {
		log.Printf("Can't open file: %s", filename)
		return err
	}
	defer f.Close()

	gz, err := gzip.NewReader(f)
	if err != nil {
		log.Printf("Can't create Reader %v", err)
		return err
	}
	defer gz.Close()

	scanner := bufio.NewScanner(gz)
	for scanner.Scan() {
		line := scanner.Text()
		line = strings.Trim(line, " ")
		if line == "" {
			continue
		}
		linesQueue <- line
	}

	if err := scanner.Err(); err != nil {
		log.Printf("Scanner error: %v", err)
		return err
	}

	return nil
}

func dotRename(path string) error {
	dir, f := filepath.Split(path)
	if err := os.Rename(path, dir+"."+f); err != nil {
		log.Printf("Can't rename a file: %s", path)
		return err
	}
	return nil
}

func mainProcess(options *Options) error {
	files, err := filepath.Glob(options.pattern)
	if err != nil {
		log.Printf("Files not found for pattern: %s", options.pattern)
		return err
	}
	resultsQueue := make(chan Result)
	memcQueues := createMemcaches(options, resultsQueue)

	deviceMemc := map[string]string{
		"idfa": idfa,
		"gaid": gaid,
		"adid": adid,
		"dvid": dvid,
	}

	for devType, memcAddr := range deviceMemc {
		memcQueues[devType] = make(chan *MemcacheItem, options.buffer)
		mc := memcache.New(memcAddr)
		go MemcacheWorker(mc, memcQueues[devType], resultsQueue)
	}

	linesQueue := make(chan string, options.buffer)
	for i := 0; i < options.workers; i++ {
		go LineParser(linesQueue, memcQueues, resultsQueue)
	}

	sort.Strings(files)
	for _, filename := range files {
		fileReader(filename, linesQueue)
		//dotRename(filename)
	}
	close(linesQueue)

	processed, errs := 0, 0
	for i := 0; i < options.workers; i++ {
		results := <-resultsQueue
		processed += results.processed
		errs += results.errors
	}

	for _, queue := range memcQueues {
		close(queue)
		results := <-resultsQueue
		processed += results.processed
		errs += results.errors

	}

	errRate := float32(errs) / float32(processed)
	if errRate < NORMAL_ERR_RATE {
		log.Printf("Acceptable error rate (%g). Successfull load\n", errRate)
	} else {
		log.Printf("High error rate (%g > %g). Failed load\n", errRate, NORMAL_ERR_RATE)
	}

	return nil
}

var (
	logfile string
	pattern string
	workers int
	buffer  int
	idfa    string
	gaid    string
	adid    string
	dvid    string
)

func init() {
	flag.StringVar(&logfile, "log", "", "")
	flag.StringVar(&pattern, "pattern", "/data/*.tsv.gz", "")
	flag.IntVar(&workers, "workers", 4, "")
	flag.IntVar(&buffer, "buffer", 100, "")
	flag.StringVar(&idfa, "idfa", "127.0.0.1:33013", "")
	flag.StringVar(&gaid, "gaid", "127.0.0.1:33014", "")
	flag.StringVar(&adid, "adid", "127.0.0.1:33015", "")
	flag.StringVar(&dvid, "dvid", "127.0.0.1:33016", "")
}

func main() {
	flag.Parse()

	options := &Options{
		logfile: logfile,
		pattern: pattern,
		workers: workers,
		buffer:  buffer,
	}

	if options.logfile != "" {
		f, err := os.OpenFile(options.logfile, os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0644)
		if err != nil {
			log.Fatalf("Cannot open log file: %s", options.logfile)
		}
		defer f.Close()
		log.SetOutput(f)
	}
	log.Println("Memc loader started with options: ", *options)
	mainProcess(options)
}
