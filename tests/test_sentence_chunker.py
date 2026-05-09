from pi_card.pipeline.sentence_chunker import chunk_sentences


def _chunks(*deltas: str) -> list[str]:
    return list(chunk_sentences(iter(deltas)))


def assert_first_chunk_emits_before_stream_drains(deltas, expected_first_chunk):
    yielded: list[str] = []

    def producer():
        for d in deltas:
            yielded.append(d)
            yield d

    first = next(chunk_sentences(producer()))

    assert first == expected_first_chunk
    assert len(yielded) < len(deltas)


def test_emits_a_chunk_at_each_sentence_boundary():
    chunks = _chunks("This is the first sentence. ", "Here is another one. ", "Done.")

    assert chunks == ["This is the first sentence.", "Here is another one.", "Done."]


def test_buffers_across_deltas_so_a_split_punct_can_arrive_alone():
    chunks = _chunks("Sentence one is long enough", ". ", "Sentence two is also long.")

    assert chunks == ["Sentence one is long enough.", "Sentence two is also long."]


def test_handles_question_marks_and_exclamation_marks():
    chunks = _chunks("Are you ready for this? ", "Absolutely we are ready! ", "Off we go.")

    assert chunks == ["Are you ready for this?", "Absolutely we are ready!", "Off we go."]


def test_flushes_remaining_text_with_no_trailing_punctuation():
    chunks = _chunks("This long sentence has no terminal punctuation")

    assert chunks == ["This long sentence has no terminal punctuation"]


def test_short_chunks_below_the_floor_are_held_back_so_abbreviations_do_not_fragment():
    chunks = _chunks("Mr. Smith arrived at the meeting. Then he left.")

    assert chunks == ["Mr. Smith arrived at the meeting.", "Then he left."]


def test_short_opening_greeting_is_emitted_without_waiting_for_a_follow_up_sentence():
    chunks = _chunks("Hi there. ", "Welcome back.")

    assert chunks == ["Hi there.", "Welcome back."]


def test_an_empty_stream_yields_nothing():
    assert _chunks() == []


def test_whitespace_only_stream_yields_nothing():
    assert _chunks("   ", "\n") == []


def test_first_chunk_is_emitted_before_the_stream_completes():
    assert_first_chunk_emits_before_stream_drains(
        deltas=["This is a long enough first sentence. ", "And here is the second sentence."],
        expected_first_chunk="This is a long enough first sentence.",
    )
