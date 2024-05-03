import json


def encoder_message(type, data, pseudo):
    return json.dumps({
        "type":type,
        "message":data,
        "pseudo":pseudo
    })


def decoder_message(data):
    return json.loads(data)