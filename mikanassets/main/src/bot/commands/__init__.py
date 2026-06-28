# commands パッケージ

INITIAL_COMMAND_PERMISSION: dict[str, int] = {
    "stop": 1, "start": 1, "exit": 2,
    "cmd serverin": 1, "cmd stdin mk": 3, "cmd stdin rm": 2,
    "cmd stdin mkdir": 2, "cmd stdin rmdir": 2, "cmd stdin ls": 2,
    "cmd stdin mv": 3, "cmd stdin send-discord": 2, "cmd stdin wget": 3,
    "help": 0, "backup create": 1, "backup apply": 3, "ip": 0,
    "logs": 1, "permission view": 0, "permission change": 4,
    "lang": 2, "tokengen": 1, "terminal set": 1, "terminal del": 1,
    "update": 3, "announce embed": 4, "status": 0,
}
