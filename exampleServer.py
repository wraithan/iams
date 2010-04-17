import iams

server = iams.ChrisIPCServer("127.0.0.1", port=9002)
total = 0
while 1:
    server.update()
    newestMessage = server.nextMessage()
    if newestMessage:
        if newestMessage[0] == "quit":
            break
        print(newestMessage[0])
        total += newestMessage[0]
        if newestMessage[2]:
            server.reply(total, newestMessage[1], newestMessage[3])


