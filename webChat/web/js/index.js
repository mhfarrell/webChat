WEB_SOCKET_SWF_LOCATION = "/js/WebSocketMain.swf";
ws_init("ws://localhost:8888/ws_channel");

$(".messages").animate({ scrollTop: $(document).height() }, "fast");

$("#profile-img").click(function() {
	$("#status-options").toggleClass("active");
});

$(".expand-button").click(function() {
  $("#profile").toggleClass("expanded");
	$("#sidebar").toggleClass("expanded");
});

$("#status-options ul li").click(function() {
	$("#profile-img").removeClass();
	$("#status-online").removeClass("active");
	$("#status-away").removeClass("active");
	$("#status-busy").removeClass("active");
	$("#status-offline").removeClass("active");
	$(this).addClass("active");
	
	if($("#status-online").hasClass("active")) {
		$("#profile-img").addClass("online");
	} else if ($("#status-away").hasClass("active")) {
		$("#profile-img").addClass("away");
	} else if ($("#status-busy").hasClass("active")) {
		$("#profile-img").addClass("busy");
	} else if ($("#status-offline").hasClass("active")) {
		$("#profile-img").addClass("offline");
	} else {
		$("#profile-img").removeClass();
	};
	
	$("#status-options").removeClass("active");
});

function ws_init(url) {

	console.log("connecting to: " + url + "...");
	ws = new WebSocket(url);
	ws.onopen = function(){	
			console.log("Connection established");
		};
	ws.onmessage = function(msg){
			var jsonMsg= JSON.parse(msg.data);
			newMessage(jsonMsg.username, jsonMsg.message);
		};
	ws.onclose = function(){
			console.log("Connection closed");
		}

};

function ws_send(user, msg){
	//form message into json string
	var msgText = '{"chatID": "1","username":"' + user + '" , "message":"' + msg + '"}';
	//send json to web socket
	ws.send(msgText);
};

function ws_close(){
	ws.close();
};


function newMessage(user, msg) {
	if($.trim(msg) == '') {
		return false;
	}
	if($('.contact-profile input').val() == user){
		$('<li class="sent"><img src="images/placeholder.png" alt="" /><p>' + msg + '</p></li>').appendTo($('.messages ul'));
		$('.message-input input').val(null);
		$('.contact.active .preview').html('<span>' + user +': </span>' + msg);
		$(".messages").animate({ scrollTop: $(document).height() }, "fast");
	}else{
		$('<li class="replies"><img src="images/placeholder.png" alt="" /><p>' + msg + '</p></li>').appendTo($('.messages ul'));
		$('.contact.active .preview').html('<span>' + user +': </span>' + msg);
		$(".messages").animate({ scrollTop: $(document).height() }, "fast");
	}
};

$('.submit').click(function() {

  ws_send($('.contact-profile input').val(),$('.message-input input').val());
});

$(window).on('keydown', function(e) {
  if (e.which == 13) {
    ws_send($('.contact-profile input').val(),$('.message-input input').val());
    return false;
  }
});