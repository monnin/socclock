function updateStatus() {
    let status = document.getElementById("status_label");

    if (status != undefined) {
        var url = window.location.href;
        var req = new XMLHttpRequest();

	url = url.replace("/menu","/show");

        req.open("GET", url, false); // sync
        req.send(null);

        val = req.responseText;

	status.innerHTML = val;
	}

    }

function pressButton(url) {
    var req = new XMLHttpRequest();
    req.open("GET", url, false); // sync
    req.send(null);

    val = req.responseText;

    if (status != undefined) {
	status.innerHTML = val;
	}
    }

setInterval(updateStatus, 1000);
