/**
 * Created by ToanDQ5 on 3/14/2017.
 */
function submit() {
    if (confirm("Are you sure ?")) {
        var data = {};
        data.imageName = $("#fileName").text();
        data.data = $("#content").html();
        $.ajax({
            type: "POST",
            data: JSON.stringify(data),
            url: "http://10.88.96.92:8013/api/markCorrectDone",
            contentType: "application/json",
            success: function (data) {
                window.location.href = "http://10.88.96.92:8013";
            },
            error: function (textStatus, errorThrown) {
                alert(errorThrown);
            }
        });
    }
}

function goBack() {
    window.history.back();
}

function editHtml(htmlPage) {
    window.location.href = "http://10.88.96.92:8013/correctPage/" + htmlPage;
}

function viewCorrectHtml(htmlPage) {
    window.location.href = "http://10.88.96.92:8013/viewCorrectPage/" + htmlPage;
}