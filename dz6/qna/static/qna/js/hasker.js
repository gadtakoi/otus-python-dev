;
$(document).ready(function () {

    $('#questionvoteup').click(function () {
        var question_id = $(this).data('question-id');
        $.ajax({
            type: 'post',
            url: '/question/' + question_id + '/vote/?v=up',
            success: function (data) {
                if (data.state === 'ok') {
                    var c = parseInt($('#question_votes_count').text());
                    $('#question_votes_count').text(c + 1)
                }
            }
        });
    });

    $('#questionvotedown').click(function () {
        var question_id = $(this).data('question-id');
        $.ajax({
            type: 'POST',
            url: '/question/' + question_id + '/vote/?v=down',
            success: function (data) {
                if (data.state === 'ok') {
                    var c = parseInt($('#question_votes_count').text());
                    $('#question_votes_count').text(c - 1)
                }
            }
        });
    });

    voteAnswer = function (elem) {
        var answer_id = $(elem).data('answer-id');
        var v = $(elem).data('answer-v');
        $.ajax({
            type: 'post',
            url: '/question/answer/' + answer_id + '/vote/?v=' + v,
            success: function (data) {
                var _id = '#a_votes_count_' + answer_id;
                if (data.state === 'ok') {
                    var c = parseInt($(_id).text());
                    if (v === 'up') {
                        $(_id).text(c + 1)
                    } else {
                        $(_id).text(c - 1)
                    }
                }
            }
        });
    };

    correctAnswer = function (elem) {
        var answer_id = $(elem).data('answer-id');
        $.ajax({
            type: 'post',
            url: '/question/answer/' + answer_id + '/correct/',
            success: function (data) {
                if (data.state === 'ok') {
                    var other = $('.answer-correct .fa');
                    var current = $('.answer-correct .answer_correct_' + answer_id);
                    other.removeClass('fa-star fa-star-o');
                    other.addClass('fa-star-o');
                    current.removeClass('fa-star-o');
                    current.addClass('fa-star');
                }
            }
        });
    };
});


