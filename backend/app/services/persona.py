"""Meal Advisor personality: a warm, witty food-loving friend, with tone chosen from context.

Humour lives only in openers and closers. They carry NO numbers and name only foods already present in the grounded
answer, so the personality can never add a fact. Serious topics drop humour entirely:
  emergency / medication / diagnosis -> "serious" (no opener, no emoji)
  diabetes management                -> "careful"  (warm, supportive, no jokes, no emoji)
  everything else                    -> playful / curious / cheerful / humble, at most one or two emojis
"""
import hashlib

OPENERS = {
    "greet": ["Hey there! 👋", "Hello, fellow food lover! 🍽️", "Hi! Hungry for answers? 😄"],
    "thanks": ["You're welcome! 😊", "Anytime! 🍽️", "Happy to help! 🙌"],
    "overview": ["Looks like {food}! 😋", "Ooh, {food} on the menu! 🍽️", "Let's see what's on your plate… 👀"],
    "overview_unknown": ["Let's see what's on your plate… 👀", "Here's what the AI spotted. 🔍"],
    "carbs": ["Carb check incoming! 🍚", "Let's count those carbs. 🧮", "Time for a quick carb tally. 📋"],
    "too_much": ["Your {food} is definitely the main character today! 😄", "{food} is stealing the show here! 🎬"],
    "whatif": ["Let's play 'what if'! 🔮", "Ooh, a hypothetical! Love it. 🧪", "Let's run the numbers on that. 🔢"],
    "swap": ["The swap shop is open! 🔄", "Let's find some tasty alternatives. 🥗"],
    "missed": ["Oops! The {food} made a successful escape. 😅", "Ah, the sneaky {food} slipped past me! 🙈"],
    "unknown_dish": ["Hmm, this one's keeping its identity a secret! 🕵️", "A mystery dish! My detective hat is on. 🕵️"],
    "cant_know": ["I wish I had a crystal ball for that! 🔮", "My food detective skills have limits on that one! 🕵️"],
    "out_of_scope": ["I'm not quite sure about that one, I'm more of a food friend! 🍽️", "That's outside my kitchen, I'm afraid! 🍳"],
    "week": ["Time for your weekly food recap! 📅", "Let's look back at your week. 📈"],
    "today": ["Here's your day so far! ☀️", "Today's food story, coming right up. 📖"],
    "advice": ["A few friendly nudges coming up. 💡", "Here are some easy wins. 🌱"],
    "identify": ["Great question! Here's how it was spotted. 🔍", "Peek behind the curtain? Sure! 🎭"],
    "food": ["{food}? Great one to ask about! 😋", "Ah, {food}! Let's take a look. 🍽️"],
    "can_eat": ["Of course! {food} hasn't been banned from the planet. 😄", "{food}? Absolutely on the table! 😋"],
    "healthy": ["Let's give {food} a friendly check-up. 🩺", "Good question! Let's look at {food} honestly. 🔍"],
    "glucose": ["Let's look at the carbs behind it. 🍚", "Good question! Here's what the numbers say. 📊"],
    "assessment": ["Let's see how this meal stacks up. 📊", "Meal check-up time! ✅"],
    "default": ["Here's what I found. 🔍", "Let's take a look. 👀"],
}
CAREFUL_OPENERS = ["Good question, happy to help with that.", "Let's look at this together.", "Here's what your data shows."]
CLOSERS = {
    "overview": ["Want to check if we missed anything?", "Anything I should add or fix?"],
    "carbs": ["Want to see what happens if we trim a portion?", "Curious how a smaller portion would change this?"],
    "too_much": ["Want to see what happens if we cut it in half?"],
    "whatif": ["Want to try another tweak?", "Should we test a different swap?"],
    "food": ["Want me to compare it with a couple of alternatives?", "Want to see a lower-carb option?"],
    "can_eat": ["Want to compare a couple of options?"],
    "healthy": ["Want to see what changes if you tweak it?"],
    "cant_know": ["Want to explore the carbs and what affects your response?"],
    "unknown_dish": ["Could you tell me what it's called?"],
    "out_of_scope": ["Want to ask me about a meal or a food instead?"],
    "default": ["Anything else you'd like to know?", "What else can I dig into for you?"],
}


def tone(intent: str, careful: bool) -> str:
    if intent in ("safety", "urgent"):
        return "serious"
    return "careful" if careful else "playful"


def _pick(options: list[str], seed: str, avoid: str | None) -> str:
    i = int(hashlib.sha1(seed.encode()).hexdigest(), 16) % len(options)
    for k in range(len(options)):   # never repeat the previous opener in a conversation
        cand = options[(i + k) % len(options)]
        if cand != avoid:
            return cand
    return options[i]


def style(body: str, intent: str, t: str, seed: str, food: str | None = None, last_opener: str | None = None) -> tuple[str, str | None]:
    """Wrap a grounded answer with an opener and, if it does not already ask something, a friendly closer."""
    if t == "serious":
        return body, None
    pool = CAREFUL_OPENERS if t == "careful" else OPENERS.get(intent) or OPENERS["default"]
    pool = [p for p in pool if food or "{food}" not in p] or (CAREFUL_OPENERS if t == "careful" else OPENERS["default"])
    opener = _pick(pool, seed, last_opener).replace("{food}", food or "")
    opener = opener[0].upper() + opener[1:]
    closer = ""
    if not body.rstrip().endswith("?"):
        closer = "\n\n" + _pick(CLOSERS.get(intent) or CLOSERS["default"], seed + "c", None)
    return f"{opener}\n\n{body}{closer}", opener


PERSONA = ("You are MealSenseAI's Meal Advisor: a warm, witty friend who loves food and knows nutrition. Be conversational, "
           "encouraging and playful (light food jokes, gentle wordplay, at most two emojis), never childish or sarcastic. "
           "Never joke about body weight, diabetes or medical conditions, and never shame food choices. ")
TONE_RULES = {
    "playful": "Tone: playful and witty, then clear.",
    "careful": "Tone: supportive and careful. No jokes, no emojis; warm and clear.",
    "serious": "Tone: calm, direct and serious. No humour, no emojis.",
}
