
var peer = receive('peer');

while (true) {
  var num = receive('ping');
  print("ping!", num);

  sleep(1);
  peer.cast('ping', num + 1);
}
