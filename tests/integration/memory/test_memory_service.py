import pytest

from supportagent.memory import service
from supportagent.memory.service import (
    delete_thread_user_turn,
    get_thread_messages,
    list_conversation_threads,
    load_memory_context,
    record_mcp_action_turn,
    save_memory_turn,
    update_thread_user_message,
)

WATER = [1.0, 0.0] + [0.0] * 1022
OTHER = [0.0, 1.0] + [0.0] * 1022


def fake_embed_texts(_client, texts):
    return [WATER if "Wasser" in text else OTHER for text in texts]


@pytest.fixture(autouse=True)
def _fake_embeddings(clean_db, monkeypatch):
    monkeypatch.setattr(service, "get_embedding_client", lambda: None)
    monkeypatch.setattr(service, "embed_texts", fake_embed_texts)


def turns(messages):
    return [(message.role, message.content) for message in messages]


# short memory
def test_saved_turn_becomes_short_memory():
    save_memory_turn("t-1", "alice", "Was ist Hausrat?", "Hausrat ist ...")

    short_memory, _ = load_memory_context("t-1", "alice", "Und weiter?")

    assert turns(short_memory) == [
        ("user", "Was ist Hausrat?"),
        ("assistant", "Hausrat ist ..."),
    ]


def test_short_memory_keeps_last_six_messages_oldest_first():
    for n in range(1, 6):
        save_memory_turn("t-1", "alice", f"q{n}", f"a{n}")

    short_memory, _ = load_memory_context("t-1", "alice", "Und weiter?")

    assert [message.content for message in short_memory] == [
        "q3",
        "a3",
        "q4",
        "a4",
        "q5",
        "a5",
    ]


# long memory
def test_most_relevant_long_memory_comes_first():
    save_memory_turn("t-1", "alice", "Kfz-Schaden melden?", "Online melden.")
    save_memory_turn("t-2", "alice", "Wasserschaden melden?", "Fotos senden.")

    _, long_memories = load_memory_context("t-3", "alice", "Wasser im Keller")

    assert "Wasserschaden" in long_memories[0].content


def test_long_memory_is_scoped_per_user():
    save_memory_turn("t-1", "alice", "Wasserschaden melden?", "Fotos senden.")

    _, long_memories = load_memory_context("t-2", "bob", "Wasser im Keller")

    assert long_memories == []


def test_mcp_action_turn_is_saved_without_long_memory():
    record_mcp_action_turn("t-1", "alice", "Termin anlegen", "Termin erstellt.")

    _, long_memories = load_memory_context("t-2", "alice", "Termin")

    assert turns(get_thread_messages("t-1", "alice")) == [
        ("user", "Termin anlegen"),
        ("assistant", "Termin erstellt."),
    ]
    assert long_memories == []


# threads
def test_thread_messages_are_only_visible_to_owner():
    save_memory_turn("t-1", "alice", "Frage", "Antwort")

    assert len(get_thread_messages("t-1", "alice")) == 2
    assert get_thread_messages("t-1", "bob") == []


def test_threads_are_listed_newest_first_for_owner():
    save_memory_turn("t-1", "alice", "Erste Frage", "Antwort")
    save_memory_turn("t-2", "alice", "Zweite Frage", "Antwort")
    save_memory_turn("t-3", "bob", "Bobs Frage", "Antwort")

    threads = list_conversation_threads("alice")

    assert [thread.thread_id for thread in threads] == ["t-2", "t-1"]
    assert threads[0].title == "Zweite Frage"
    assert threads[0].message_count == 2


# edit and delete
def test_editing_question_removes_its_answer():
    save_memory_turn("t-1", "alice", "Frage", "Antwort")
    [question, _] = get_thread_messages("t-1", "alice")

    assert update_thread_user_message("t-1", "alice", question.id, "Neue Frage")
    assert turns(get_thread_messages("t-1", "alice")) == [("user", "Neue Frage")]


def test_other_user_cannot_edit_question():
    save_memory_turn("t-1", "alice", "Frage", "Antwort")
    [question, _] = get_thread_messages("t-1", "alice")

    assert not update_thread_user_message("t-1", "bob", question.id, "Gehackt")
    assert len(get_thread_messages("t-1", "alice")) == 2


def test_deleting_question_removes_whole_turn():
    save_memory_turn("t-1", "alice", "Frage", "Antwort")
    [question, _] = get_thread_messages("t-1", "alice")

    assert delete_thread_user_turn("t-1", "alice", question.id)
    assert get_thread_messages("t-1", "alice") == []


# thread ownership
def test_other_user_cannot_read_thread_via_short_memory():
    save_memory_turn("t-1", "alice", "Meine Policennummer ist 123", "Notiert.")
    short_memory, _ = load_memory_context("t-1", "bob", "Was weißt du?")
    assert short_memory == []


def test_other_user_cannot_take_over_thread():
    save_memory_turn("t-1", "alice", "Frage", "Antwort")

    save_memory_turn("t-1", "bob", "Bobs Frage", "Bobs Antwort")

    assert [thread.thread_id for thread in list_conversation_threads("alice")] == [
        "t-1"
    ]
    assert list_conversation_threads("bob") == []
    assert turns(get_thread_messages("t-1", "alice")) == [
        ("user", "Frage"),
        ("assistant", "Antwort"),
    ]
