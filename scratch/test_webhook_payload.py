from app.schemas.webhook import Payload

# Test input payload resembling the real webhook structure
test_payload_data = {
    "event": "message",
    "sessionId": "test-session",
    "data": {
        "messages": {
            "key": {
                "id": "12345",
                "fromMe": False,
                "remoteJid": "123456789@s.whatsapp.net"
            },
            "messageTimestamp": {"low": 1779822476, "high": 0, "unsigned": True},
            "pushName": "Kamel",
            "message": {
                "extendedTextMessage": {
                    "text": "Hello world!"
                }
            }
        }
    },
    "timestamp": {"low": 1779822480, "high": 0, "unsigned": True}
}

try:
    payload = Payload(**test_payload_data)
    print("SUCCESS: Payload parsed successfully!")
    print("messageTimestamp:", payload.data.messages.messageTimestamp)
    print("timestamp:", payload.timestamp)
except Exception as e:
    print("FAILURE: Error parsing payload:")
    import traceback
    traceback.print_exc()
