
var urlprefix = ".ip.suysker.top"
var imgUrls = ["/img/s.jpg", "/img/m.jpg", "/img/l.png"]
var imgBytes = [118221, 1531677, 10830957]
var imgi = 1
var concurrency = parseInt($("#concurrency-input").val());
var respondTimeout = parseInt($("#ping-timeout-input").val());
var speedTimeout = parseInt($("#http-timeout-input").val());
var page = 50
var idn = 0
var database = {}
var previousRegions = [];
var currentProvider = 'Cloudflare'
var filename = 'simple_reachable_ips'

function isIPv6(ip) {
    return ip.includes(":");
}

$(".ip-button").click(function () {
    $(".ip-button").css("background-color", "grey");
    $(this).css("background-color", "green");
});

$(".provider-button").click(function () {
    $(".provider-button").css("background-color", "grey");
    $(this).css("background-color", "green");
});

// Main Table
options = {
    selectable: true,
    layout: "fitDataTable",
    downloadRowRange: "selected",
    rowSelected: function (row) {
        select_1()
    },
    rowDeselected: function (row) {
        var selectedRows = table.getSelectedRows()
        if (selectedRows.length == 0)
            select_0()
    },
    columns: [
        { title: "IP address", field: "ip" },
        { title: "Region", field: "region" },
        {
            title: "Mean Respond Time", field: "time", sorter: "number", sorterParams: {
                alignEmptyValues: "bottom",
            }
        },
        {
            title: "Mean Download Speed", field: "speed", sorter: "number", sorterParams: {
                alignEmptyValues: "bottom",
            }
        },
    ],
}
if (typeof (page) != 'undefined' && page) {
    options.pagination = "local" // pagination may cause problem in mobile devices
    options.paginationSize = 100
}
table = new Tabulator("#main-table", options)


// Panel
function select_0() {
    $("#select-all").attr("data-status", 0)
    $("#select-all").text("Select All")
}
function select_1() {
    $("#select-all").attr("data-status", 1)
    $("#select-all").text("Deselect All")
}
$("#select-all").click(function () {
    if ($("#select-all").attr("data-status") == 0) {
        table.selectRow()
        select_1()
    } else {
        table.deselectRow()
        select_0()
    }
})

$("#select-random").click(function () {
    table.deselectRow()
    var idList = []
    var cList = []
    var sn = $("#select-number").val()
    table.getRows().forEach(function (one) {
        idList.push(one.getData().id)
    })
    for (var i = 0; i < sn; i++) {
        var s = Math.floor(Math.random() * idList.length)
        cList.push(idList.splice(s, 1)[0])

    }
    table.selectRow(cList.sort())
})

$("#download").click(function () {
    table.download("csv", "test_result.csv", { bom: true })
    // include BOM to ensure that UTF-8 characters can be correctly interpereted
})


// Respond time test
function tcpingCallback(time, id) {
    database[id].time.push(time)
    var alln = database[id].time.length
    var validset = []
    var sum = 0
    database[id].time.forEach(function (one) {
        if (one > 0) {
            validset.push(one)
            sum += one
        }
    })
    var validn = validset.length
    var mean = sum / validn
    var str = ""
    if (validn > 1) {
        str = " (" + validn + "/" + alln + ")"
        var sumsq = 0
        validset.forEach(function (one) {
            sumsq += Math.pow(one - mean, 2)
        })
        var std = Math.sqrt(sumsq / validn)
        str = mean.toFixed(1) + "ms" + " σ=" + std.toFixed(1) + str
    }
    else if (validn == 1) {
        str = mean.toFixed(1) + "ms" + str
    }
    else {
        str = "Timeout" + str
    }
    table.updateData([{ id: id, time: str }])
}

function tcping(addr, callback, id, resolve) {
    var started = window.performance.now();
    var http = new XMLHttpRequest();

    http.open("GET", addr, true);

    http.onreadystatechange = function () {
        if (http.readyState == 2) {
            var ended = window.performance.now();
            var milliseconds = ended - started;
            callback(milliseconds, id);
            resolve();
        }
    };

    http.onerror = function () {
        var ended = window.performance.now();
        var milliseconds = ended - started;

        if (currentProvider === "CloudFront" || currentProvider === "Gcore") {
            // 认为连接断开是成功的，返回估算的响应时间
            callback(milliseconds, id);
        } else {
            callback(-1, id);
        }
        resolve();
    };

    http.onload = function () {
        var resp = http.responseText;
        var loc = resp.split("\n")[6].split("=")[1];
        table.updateData([{ id: id, region: loc }]);
    };

    http.timeout = respondTimeout;

    http.ontimeout = function () {
        callback(-1, id);  // Indicate timeout with -1
        resolve();
    };

    http.send(null);
}

var positionSort = function (a, b) {
    return a.getPosition(true) - b.getPosition(true)
}



$("#test-respond").click(async function () {
    respondTimeout = parseInt($("#ping-timeout-input").val());
    concurrency = parseInt($("#concurrency-input").val());
    var selectedRows = table.getSelectedRows();
    var sn = selectedRows.length;
    // 根据currentProvider判断是否使用http或https
    var protocol = (currentProvider === "Gcore") ? "https" : "http";
    var pingUrl = (currentProvider === "Cloudflare") ? "/cdn-cgi/trace" : "";

    if (sn > 0) {
        $("#test-respond").prop("disabled", true);
        selectedRows.sort(positionSort);

        for (let i = 0; i < sn; i += concurrency) {
            let batch = selectedRows.slice(i, i + concurrency);
            await Promise.all(batch.map(row => {
                return new Promise(resolve => {
                    var one = row.getData();
                    addr = protocol + "://" + (isIPv6(one.ip) ? "[" + one.ip + "]" : one.ip) + pingUrl + "?" + Math.random();
                    tcping(addr, tcpingCallback, one.id, resolve);  // 注意这里，传递resolve作为参数
                });
            }));
        }

        table.redraw(true);
        $("#test-respond").prop("disabled", false);
    }
});


// Speed test
function speedProgressCallback(rbytes, time, id) {
    var rate = rbytes / imgBytes[imgi] * 100
    var speed = (rbytes / 1024) / (time / 1000)
    var str = speed.toFixed(1) + " KB/s " + rate.toFixed(1) + " %"
    table.updateData([{ id: id, speed: str }])
}

function speedEndCallback(rbytes, time, id) {
    var speed = (rbytes / 1024) / (time / 1000)
    database[id].speed.push(speed)
    var alln = database[id].speed.length
    var validset = []
    var sum = 0
    database[id].speed.forEach(function (one) {
        if (one > 0 && rbytes / imgBytes[imgi] > 0.05) { // in case 403
            validset.push(one)
            sum += one
        }
    })
    var validn = validset.length
    var mean = sum / validn
    var str = ""
    if (validn > 1) {
        str = " (" + validn + "/" + alln + ")"
        var sumsq = 0
        validset.forEach(function (one) {
            sumsq += Math.pow(one - mean, 2)
        })
        var std = Math.sqrt(sumsq / validn)
        str = mean.toFixed(1) + " KB/s" + " σ=" + std.toFixed(1) + str
    }
    else if (validn == 1) {
        str = mean.toFixed(1) + " KB/s" + str
    }
    else {
        str = "Error" + str
    }
    table.updateData([{ id: id, speed: str }])

}


function speedRecur(list, i, resolve) {
    if (i >= list.length) {
        table.redraw(true);
        $("#test-speed").prop("disabled", false);
        $("#img-select").prop("disabled", false);
        return;
    }
    var one = list[i];
    var id = one.id;
    var addr = one.addr;
    var started = window.performance.now();
    var http = new XMLHttpRequest();
    http.open("GET", addr, true);
    http.onreadystatechange = function () {
        // ... (keep the existing code here unchanged)
    };
    http.loadr = 0;
    http.onloadend = function (e) {
        var rbytes = (e.loaded == 0) ? http.loadr : e.loaded;
        var ended = window.performance.now();
        var milliseconds = ended - started;
        speedEndCallback(rbytes, milliseconds, id);

        // Move on to the next IP in the list
        if (i === list.length - 1) {
            resolve();
        } else {
            // Otherwise, move on to the next IP in the list
            speedRecur(list, i + 1, resolve);
        }
    };
    http.onprogress = function (e) {
        var rbytes = e.loaded;
        http.loadr = rbytes;
        var ended = window.performance.now();
        var milliseconds = ended - started;
        if (milliseconds > 100)
            speedProgressCallback(rbytes, milliseconds, id);
    };
    http.timeout = speedTimeout;
    http.ontimeout = function () {
        if (callback != null) {
            callback(-1, id);
            callback = null;
        }
    };
    http.send();
}


$("#test-speed").click(async function () {
    speedTimeout = parseInt($("#http-timeout-input").val());
    concurrency = parseInt($("#concurrency-input").val());
    var selectedRows = table.getSelectedRows();
    var sn = selectedRows.length;

    if (sn > 0) {
        $("#test-speed").prop("disabled", true);
        $("#img-select").prop("disabled", true);
        selectedRows.sort(positionSort);

        var sList = [];
        selectedRows.forEach(function (row) {
            var one = row.getData();
            var ip = one.ip.endsWith("::") ? one.ip.slice(0, -2) : one.ip;
            sList.push({
                id: one.id,
                addr: "//" + (isIPv6(ip) ? ip.replace("::", "-").replace(/:/g, "-") : ip.replace(/\./g, "-")) + urlprefix + imgUrls[imgi] + "?" + Math.random()
            });
        });

        for (let i = 0; i < sn; i += concurrency) {
            let batch = sList.slice(i, i + concurrency);

            // Wait for all items in the current batch to complete
            await Promise.all(batch.map(item => {
                return new Promise(resolve => {
                    // Modified speedRecur to accept a resolve function, which will be called at the end
                    speedRecur([item], 0, resolve);
                });
            }));
        }

        table.redraw(true);
        $("#test-speed").prop("disabled", false);
        $("#img-select").prop("disabled", false);
    }
});



function setupButtons(buttonClass, updateFunction) {
    if (typeof updateFunction !== "function") {
        return; // 如果不是函数，就退出
    }
    document.querySelectorAll(buttonClass).forEach(function (button) {
        button.addEventListener('click', function () {
            updateFunction(this.id);
            fetchData();
        });
    });
}

function updateCurrentProvider(value) {
    currentProvider = value;

    // 当选择Gcore或CloudFront时，禁用test-speed按钮
    if (currentProvider === "Gcore" || currentProvider === "CloudFront") {
        console.log("Disabling test-speed button"); // 输出禁用信息
        $("#test-speed").prop("disabled", true);
    } else {
        console.log("Enabling test-speed button"); // 输出启用信息
        $("#test-speed").prop("disabled", false);
    }
}

function updateFilename(value) {
    filename = value;
}

function fetchData() {
    let url = `https://raw.githubusercontent.com/Suysker/IP-Check/main/${currentProvider}/${filename}.txt`;

    if (currentProvider === "CloudFront") {
        url = `https://raw.githubusercontent.com/Suysker/IP-Check/main/${currentProvider}/geo_${filename}.txt`;
    }
    $.get(url, function (data) {
        tablemake(data);
    }).fail(function () {
        if (currentProvider === "CloudFront") {
            $.get(`/${currentProvider}/geo_${filename}.txt`, tablemake);
        } else {
            $.get(`/${currentProvider}/${filename}.txt`, tablemake);
        }
    });
}

document.addEventListener("DOMContentLoaded", function () {
    setupButtons('.provider-button', updateCurrentProvider);
    setupButtons('.ip-button', updateFilename);

    // 在页面加载完成后立即执行初始化
    fetchData();
});


// Entry
function tablemake(data) {
    var initData = [];
    ip_list = data.split("\n");
    
    // 过滤空字符串
    ip_list = ip_list.filter(item => item.trim() !== "");

    ip_list.forEach(function (line) {
        let parts = line.split(/\s+/);  // Split by one or more spaces
        let one_ip, region;

        if (parts.length > 1) {
            // Format: IP region (for CloudFront)
            one_ip = parts[0];
            region = parts[1];
        } else {
            // Format: IP
            one_ip = parts[0];
            region = "";
        }

        initData.push({
            id: idn,
            ip: one_ip,
            region: region,
            time: "",
            speed: ""
        });

        database[idn] = {
            time: [],
            speed: []
        };
        idn += 1;
    });

    table.replaceData(initData);
    $("#select-number").attr("max", idn);
}


$("#region-select").on('focus touchstart click', function() {
    var regions = [];
    
    // Get all rows from the table
    var rows = table.getRows();
    rows.forEach(function(row) {
        var region = row.getData().region; // Assuming the column key for regions is "region"
        if (region && regions.indexOf(region) === -1) { // Ensure the region is not empty
            regions.push(region);
        }
    });

    // Sort regions alphabetically
    regions.sort();

    // Add "All" to the beginning of the sorted regions array
    regions.unshift("All");

    // Check if regions have changed
    if (JSON.stringify(regions) !== JSON.stringify(previousRegions)) {
        var selectDropdown = $(this);  // Using 'this' since we are inside the click event of the dropdown
        selectDropdown.empty();  // Using jQuery's .empty() to clear the dropdown
        
        // Add new options to the dropdown
        regions.forEach(function(region) {
            var option = $("<option>").val(region).text(region);
            selectDropdown.append(option);
        });

        // Save the new regions as the previous ones for the next check
        previousRegions = regions.slice();
    }
});


$("#test-region-button").click(function () {
    var selectedRegion = document.getElementById("region-select").value;
    if(selectedRegion) {
        // Deselect all rows first
        table.deselectRow();
        
        // Select rows based on the selected region
        var rows = table.getRows();
        rows.forEach(function(row) {
            if (selectedRegion === "All" && row.getData().region) {
                row.select();
            } else if (row.getData().region === selectedRegion) {
                row.select();
            }
        });
    }
});
