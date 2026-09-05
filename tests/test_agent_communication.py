from civilizations.agent_communication import AgentCommunicationBus, CommunicationConfig


def test_publish_and_inbox(tmp_path):
    bus = AgentCommunicationBus(CommunicationConfig(root=tmp_path))
    msg = bus.publish("A001", "A002", "research", "Liquidity is improving on the observed venue.")
    assert msg.sender == "A001"
    assert bus.inbox("A002")[0].message_id == msg.message_id


def test_broadcast_and_topic_filter(tmp_path):
    bus = AgentCommunicationBus(CommunicationConfig(root=tmp_path))
    messages = bus.broadcast("A001", ["A002", "A003", "A002"], "idea", "Test the hypothesis.")
    assert len(messages) == 2
    assert len(bus.inbox("A003", topic="idea")) == 1
    assert bus.inbox("A003", topic="other") == []


def test_communication_is_audited(tmp_path):
    bus = AgentCommunicationBus(CommunicationConfig(root=tmp_path))
    bus.publish("A001", "A002", "debate", "Challenge my assumptions.")
    audit = (tmp_path / "communication_audit.jsonl").read_text()
    assert "A001" in audit and "A002" in audit and "publish" in audit


def test_oversized_message_is_rejected(tmp_path):
    config = CommunicationConfig(root=tmp_path, max_message_bytes=10)
    bus = AgentCommunicationBus(config)
    try:
        bus.publish("A001", "A002", "research", "01234567890")
    except ValueError as exc:
        assert "size limit" in str(exc)
    else:
        raise AssertionError("oversized message was accepted")


def test_path_like_agent_ids_are_rejected(tmp_path):
    bus = AgentCommunicationBus(CommunicationConfig(root=tmp_path))
    try:
        bus.publish("../A001", "A002", "research", "unsafe")
    except ValueError:
        pass
    else:
        raise AssertionError("unsafe agent id was accepted")
