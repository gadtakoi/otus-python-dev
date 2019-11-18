#### Clone repo
```bash
git clone https://github.com/gadtakoi/otus-python-dev.git
```

#### Clone cpython
```bash
git clone https://github.com/python/cpython.git
cp otus-python-dev/dz2/*.patch cpython/
cd cpython
git checkout 2.7
```

# Homeworks
## Opcode
#### Compile for python 2.7
```bash
git apply new_opcode.patch
./configure --with-pydebug --prefix=/tmp/python
make -j2
```
#### Test Opcode:
```bash
./python
```

```python
def fib(n): return fib(n - 1) + fib(n - 2) if n > 1 else n

import dis
dis.dis(fib)
```

## Until
#### Compile for python 2.7
```bash
git apply until.patch
make regen-grammar
python ./Parser/asdl_c.py -h ./Include ./Parser/Python.asdl
python ./Parser/asdl_c.py -c ./Python ./Parser/Python.asdl
./configure --with-pydebug --prefix=/tmp/python
make -j2
```

##### Test Until:
```bash
./python
```

```python
num = 3
until num == 0:
     print(num)
     num -= 1
```

## Increment/decrement
#### Compile for python 3.8
```bash
git checkout .
git checkout 3.8
git apply inc.patch

make regen-grammar
python3 Parser/asdl_c.py  ./Parser/Python.asdl
./configure --with-pydebug --prefix=/tmp/python
make -j2
```

#### Test Increment/decrement:
```bash
./python
```

```python
test = 1
test ++
test
```