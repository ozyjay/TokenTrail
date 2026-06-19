"""Scripted token traces for the first Token Trail MVP.

The initial Open Day version should be useful even when no live model is
available. These traces drive the visualiser and can later be replaced or
augmented by a local model backend.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence


@dataclass(frozen=True)
class CandidateToken:
    """A possible next token shown to visitors."""

    token: str
    probability: float


@dataclass(frozen=True)
class GenerationStep:
    """One visible next-token prediction step."""

    selected_token: str
    candidates: tuple[CandidateToken, ...]
    explanation: str


@dataclass(frozen=True)
class TokenTrace:
    """A replayable prompt and token-by-token generation trace."""

    id: str
    title: str
    prompt: str
    prompt_tokens: tuple[str, ...]
    steps: tuple[GenerationStep, ...]

    @property
    def generated_text(self) -> str:
        return join_tokens(step.selected_token for step in self.steps)

    def to_dict(self) -> dict:
        return asdict(self)


def simple_tokenise(text: str) -> tuple[str, ...]:
    """Small display-focused tokeniser.

    This is intentionally simple. It is not claiming to match a production LLM
    tokenizer. It gives the MVP clear, visible token blocks while the real
    tokenizer adapter is still future work.
    """

    spaced = text.replace(".", " .").replace(",", " ,").replace(":", " :")
    return tuple(part for part in spaced.split() if part)


def join_tokens(tokens: Sequence[str]) -> str:
    """Join display tokens into readable text."""

    text = " ".join(tokens)
    return text.replace(" .", ".").replace(" ,", ",").replace(" :", ":")


TRACE_LIBRARY: tuple[TokenTrace, ...] = (
    TokenTrace(
        id="robot-university",
        title="Robot at university",
        prompt="Write a short story about a robot at university.",
        prompt_tokens=simple_tokenise("Write a short story about a robot at university."),
        steps=(
            GenerationStep(
                selected_token="A",
                candidates=(
                    CandidateToken("A", 0.42),
                    CandidateToken("The", 0.27),
                    CandidateToken("One", 0.18),
                ),
                explanation="Common story openings are likely after this prompt.",
            ),
            GenerationStep(
                selected_token="small",
                candidates=(
                    CandidateToken("small", 0.31),
                    CandidateToken("curious", 0.24),
                    CandidateToken("student", 0.16),
                ),
                explanation="The next token narrows the kind of robot in the story.",
            ),
            GenerationStep(
                selected_token="robot",
                candidates=(
                    CandidateToken("robot", 0.56),
                    CandidateToken("drone", 0.14),
                    CandidateToken("machine", 0.11),
                ),
                explanation="The prompt mentioned a robot, so that continuation is strongly favoured.",
            ),
            GenerationStep(
                selected_token="joined",
                candidates=(
                    CandidateToken("joined", 0.29),
                    CandidateToken("entered", 0.21),
                    CandidateToken("visited", 0.18),
                ),
                explanation="The model continues with an action that fits a university setting.",
            ),
            GenerationStep(
                selected_token="orientation",
                candidates=(
                    CandidateToken("orientation", 0.33),
                    CandidateToken("class", 0.24),
                    CandidateToken("campus", 0.15),
                ),
                explanation="University context makes words like orientation, class, and campus plausible.",
            ),
            GenerationStep(
                selected_token="and",
                candidates=(
                    CandidateToken("and", 0.37),
                    CandidateToken(".", 0.25),
                    CandidateToken(",", 0.17),
                ),
                explanation="The sentence can continue or end; sampling chooses one path.",
            ),
            GenerationStep(
                selected_token="learned",
                candidates=(
                    CandidateToken("learned", 0.34),
                    CandidateToken("found", 0.21),
                    CandidateToken("asked", 0.19),
                ),
                explanation="The generated story now moves toward a learning outcome.",
            ),
            GenerationStep(
                selected_token="to",
                candidates=(
                    CandidateToken("to", 0.61),
                    CandidateToken("that", 0.15),
                    CandidateToken("from", 0.07),
                ),
                explanation="Some tokens are highly predictable because of grammar.",
            ),
            GenerationStep(
                selected_token="ask",
                candidates=(
                    CandidateToken("ask", 0.33),
                    CandidateToken("code", 0.21),
                    CandidateToken("listen", 0.13),
                ),
                explanation="The model chooses a likely continuation, not a guaranteed fact.",
            ),
            GenerationStep(
                selected_token="better",
                candidates=(
                    CandidateToken("better", 0.36),
                    CandidateToken("clear", 0.17),
                    CandidateToken("helpful", 0.16),
                ),
                explanation="This token shapes the final message of the sentence.",
            ),
            GenerationStep(
                selected_token="questions",
                candidates=(
                    CandidateToken("questions", 0.49),
                    CandidateToken("directions", 0.16),
                    CandidateToken("code", 0.11),
                ),
                explanation="The story ends with a university-friendly learning idea.",
            ),
            GenerationStep(
                selected_token=".",
                candidates=(
                    CandidateToken(".", 0.72),
                    CandidateToken("before", 0.08),
                    CandidateToken("with", 0.06),
                ),
                explanation="A full stop is likely once the sentence is complete.",
            ),
        ),
    ),
    TokenTrace(
        id="mars-greenhouse",
        title="Mars greenhouse",
        prompt="Explain how a greenhouse could help astronauts grow food on Mars.",
        prompt_tokens=simple_tokenise("Explain how a greenhouse could help astronauts grow food on Mars."),
        steps=(
            GenerationStep(
                selected_token="A",
                candidates=(
                    CandidateToken("A", 0.39),
                    CandidateToken("The", 0.24),
                    CandidateToken("Mars", 0.18),
                ),
                explanation="Explanations often begin with a noun phrase that introduces the main idea.",
            ),
            GenerationStep(
                selected_token="greenhouse",
                candidates=(
                    CandidateToken("greenhouse", 0.52),
                    CandidateToken("habitat", 0.17),
                    CandidateToken("garden", 0.12),
                ),
                explanation="The prompt makes greenhouse the most likely next content word.",
            ),
            GenerationStep(
                selected_token="would",
                candidates=(
                    CandidateToken("would", 0.46),
                    CandidateToken("could", 0.31),
                    CandidateToken("can", 0.09),
                ),
                explanation="The sentence is setting up a practical explanation rather than a story event.",
            ),
            GenerationStep(
                selected_token="protect",
                candidates=(
                    CandidateToken("protect", 0.34),
                    CandidateToken("give", 0.21),
                    CandidateToken("hold", 0.16),
                ),
                explanation="Mars is harsh, so protection is a likely concept.",
            ),
            GenerationStep(
                selected_token="plants",
                candidates=(
                    CandidateToken("plants", 0.57),
                    CandidateToken("seeds", 0.15),
                    CandidateToken("astronauts", 0.11),
                ),
                explanation="The object of protection follows from growing food.",
            ),
            GenerationStep(
                selected_token="from",
                candidates=(
                    CandidateToken("from", 0.63),
                    CandidateToken("with", 0.14),
                    CandidateToken("inside", 0.08),
                ),
                explanation="Grammar strongly favours from after protect plants.",
            ),
            GenerationStep(
                selected_token="cold",
                candidates=(
                    CandidateToken("cold", 0.31),
                    CandidateToken("radiation", 0.27),
                    CandidateToken("dust", 0.22),
                ),
                explanation="Several Mars hazards are plausible; sampling chooses one.",
            ),
            GenerationStep(
                selected_token="and",
                candidates=(
                    CandidateToken("and", 0.49),
                    CandidateToken(".", 0.18),
                    CandidateToken(",", 0.13),
                ),
                explanation="The model continues the list of hazards.",
            ),
            GenerationStep(
                selected_token="dust",
                candidates=(
                    CandidateToken("dust", 0.36),
                    CandidateToken("radiation", 0.29),
                    CandidateToken("dryness", 0.11),
                ),
                explanation="Dust is another common Mars-related continuation.",
            ),
            GenerationStep(
                selected_token=".",
                candidates=(
                    CandidateToken(".", 0.68),
                    CandidateToken("while", 0.12),
                    CandidateToken("so", 0.08),
                ),
                explanation="A full stop completes a short public-demo sentence.",
            ),
        ),
    ),
    TokenTrace(
        id="library-dragon",
        title="Library dragon",
        prompt="Write a tiny story about a dragon helping in a library.",
        prompt_tokens=simple_tokenise("Write a tiny story about a dragon helping in a library."),
        steps=(
            GenerationStep(
                selected_token="The",
                candidates=(
                    CandidateToken("The", 0.35),
                    CandidateToken("A", 0.32),
                    CandidateToken("One", 0.16),
                ),
                explanation="Story prompts often begin with a simple article.",
            ),
            GenerationStep(
                selected_token="dragon",
                candidates=(
                    CandidateToken("dragon", 0.58),
                    CandidateToken("librarian", 0.13),
                    CandidateToken("little", 0.1),
                ),
                explanation="The prompt names a dragon, making it a likely subject.",
            ),
            GenerationStep(
                selected_token="sorted",
                candidates=(
                    CandidateToken("sorted", 0.28),
                    CandidateToken("guarded", 0.2),
                    CandidateToken("carried", 0.17),
                ),
                explanation="The library setting pushes the story toward book-related actions.",
            ),
            GenerationStep(
                selected_token="books",
                candidates=(
                    CandidateToken("books", 0.55),
                    CandidateToken("shelves", 0.19),
                    CandidateToken("scrolls", 0.1),
                ),
                explanation="Books are a natural object after sorted in this setting.",
            ),
            GenerationStep(
                selected_token="with",
                candidates=(
                    CandidateToken("with", 0.44),
                    CandidateToken("and", 0.23),
                    CandidateToken("into", 0.12),
                ),
                explanation="The next token can introduce the dragon's special method.",
            ),
            GenerationStep(
                selected_token="gentle",
                candidates=(
                    CandidateToken("gentle", 0.33),
                    CandidateToken("tiny", 0.24),
                    CandidateToken("careful", 0.19),
                ),
                explanation="A public-friendly story favours safe, helpful words.",
            ),
            GenerationStep(
                selected_token="puffs",
                candidates=(
                    CandidateToken("puffs", 0.37),
                    CandidateToken("claws", 0.17),
                    CandidateToken("wings", 0.16),
                ),
                explanation="Dragon imagery makes puffs a plausible continuation.",
            ),
            GenerationStep(
                selected_token="of",
                candidates=(
                    CandidateToken("of", 0.71),
                    CandidateToken("and", 0.08),
                    CandidateToken(",", 0.06),
                ),
                explanation="Puffs is commonly followed by of.",
            ),
            GenerationStep(
                selected_token="warm",
                candidates=(
                    CandidateToken("warm", 0.34),
                    CandidateToken("blue", 0.17),
                    CandidateToken("golden", 0.15),
                ),
                explanation="The selected adjective keeps the sentence friendly and vivid.",
            ),
            GenerationStep(
                selected_token="air",
                candidates=(
                    CandidateToken("air", 0.42),
                    CandidateToken("smoke", 0.21),
                    CandidateToken("light", 0.12),
                ),
                explanation="Warm air fits both dragon breath and a calm library.",
            ),
            GenerationStep(
                selected_token=".",
                candidates=(
                    CandidateToken(".", 0.74),
                    CandidateToken("until", 0.07),
                    CandidateToken("while", 0.06),
                ),
                explanation="The generated sentence is complete.",
            ),
        ),
    ),
)


def list_traces() -> list[dict]:
    """Return trace metadata for the UI."""

    return [
        {
            "id": trace.id,
            "title": trace.title,
            "prompt": trace.prompt,
            "prompt_tokens": trace.prompt_tokens,
            "step_count": len(trace.steps),
        }
        for trace in TRACE_LIBRARY
    ]


def get_trace(trace_id: str) -> TokenTrace:
    """Look up a trace by id."""

    for trace in TRACE_LIBRARY:
        if trace.id == trace_id:
            return trace
    raise KeyError(f"Unknown trace id: {trace_id}")
