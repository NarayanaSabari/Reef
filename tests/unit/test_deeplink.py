from reef.shell.deeplink import encode_deeplink, decode_deeplink, DeepLink

def test_encode_decode_roundtrip():
    payload = encode_deeplink("morning_brief", brief="2 PRs, 1 meeting")
    dl = decode_deeplink(payload)
    assert dl == DeepLink(action="morning_brief", context={"brief": "2 PRs, 1 meeting"})

def test_decode_non_reef_payload_returns_none():
    assert decode_deeplink({"foo": "bar"}) is None

def test_encode_with_no_context():
    dl = decode_deeplink(encode_deeplink("open_chat"))
    assert dl.action == "open_chat" and dl.context == {}
