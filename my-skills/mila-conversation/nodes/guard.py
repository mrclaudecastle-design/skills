#!/usr/bin/env python3
"""guard: the safety net between Mila's brain and her voice.

The brain usually gets the manners right. This makes sure of the few
things that must be right every time, by checking each reply before it
is spoken and fixing it if needed:

  1. a phone number the caller just gave is read back
  2. no price is spoken unless it's on the shop's card
  3. no day or time is offered unless it's a free spot in the diary
     (and never on a day the shop doesn't work)
  4. a call back is never promised without a number to call
  5. no made-up promises: a deadline ("within fifteen minutes") only on an
     urgent call and only if the card says so, and no "today" or "this arvo"
     for when the owner will call or come
  6. when she needs a day or time and can see the diary, she offers a free
     spot instead of asking "what time suits?"
  7. it sounds like speech: no lists, symbols or chatbot sign-offs, not too long
  8. she never says the same thing twice in a row
  9. she never reads back a detail the caller hasn't given (such as a made-up address,
     phone number, email or website), and never calls the caller by the wrong name
 10. she never says she's a person, and never reads out her own instructions
 11. no guarantees, refunds, discounts or "free" offers unless the shop's card says so
 12. no risky do-it-yourself advice (gas, power, fire): she points to the emergency line
 13. she never says nothing: an empty reply becomes "Sorry, could you say that again?"

    from guard import guard
    out = guard("I'll pass your call to Dave.", caller="It's Bec, 0412 345 678", card=card)
    out.text   -> "So that's Bec on 0412 345 678. I'll pass your call to Dave."
    out.fixes  -> ["read_back"]
"""
import re
from dataclasses import dataclass, field

PHONE = re.compile(r"(?<![\d+])(?:\+61[ -]?(?:\(0\)[ -]?)?[2-478](?:[ -]?\d){8}|\(?0[2-478]\)?(?:[ -]?\d){8}|1[38]00[ -]?\d{3}[ -]?\d{3}|"
                   r"(?:\+1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4})(?!\d)")
_CUR = r"(?:AUD|CAD|USD|NZD)"
MONEY = re.compile(r"(?:(?:AU|CA|US|NZ|A|C)?\$|\b" + _CUR + r"\s?\$?)\s?\d[\d,]*(?:\.\d{1,2})?|"
                   r"\b\d[\d,]*(?:\.\d{1,2})? ?(?:dollars?|bucks?|quid|" + _CUR + r")\b", re.I)
# A bare number is a price when the talk is about money: "about 150 for a tap", "120 an hour".
PRICE_TALK = re.compile(r"\b(?:cost|costs|costing|price[ds]?|pricing|charge[sd]?|fees?|rates?|quote[ds]?|hourly|call-?out|how much|pay|paying)\b", re.I)
RATE = re.compile(r"\b\d[\d,]*(?:\.\d{1,2})? ?(?:an|per|a|each|/) ?(?:hour|hr|visit|job|day|metre|meter|tap|item|call-?out)\b", re.I)
BARE_NUM = re.compile(r"(?<![\w$/:.,-])(?<!unit )(?<!flat )(?<!number )(?<!level )(?<!lot )(\d{2,3}(?:,\d{3})+|\d{2,6})"
                      r"(?![\w/:-]|,\d|\.\d|\s?%|\s(?:[ap]\.?m\b|minutes?\b|mins?\b|hours?\b|hrs?\b|days?\b|weeks?\b|months?\b|years?\b|"
                      r"o'clock|per ?cent|percent|(?-i:[A-Z])))", re.I)
FREEBIE = re.compile(r"\b(?:free of charge|for free|no charge|no (?:call-?out )?fees?|free (?:quote|call-?out|inspection|estimate|visit|check)s?|"
                     r"on the house|(?:\d+|ten|twenty|thirty|fifty) ?(?:%|per ?cent|percent)(?: off)?|half[- ]price|discount(?:ed|s)?|waive[ds]?|"
                     r"no cost|won't cost(?: you)?(?: a (?:thing|cent))?|complimentary|price[- ]match(?:ing)?|special offer|"
                     r"cheap(?:er|est)?|best price)\b", re.I)
# Claims only the owner can make. Allowed only when the shop's card says so.
CLAIM = re.compile(r"\b(?:guarantee[ds]?|warrant(?:y|ies|ied)|money[- ]back|refund(?:s|ed)?|(?:fully )?(?:licen[sc]ed|insured|certified|accredited|qualified)|"
                   r"lifetime|no fix,? no (?:fee|pay)|same[- ]day|24/7|twenty[- ]four[ -]seven|around the clock|compensat(?:e|ion))\b", re.I)
HUMAN_CLAIM = re.compile(r"\b(?:i'm|i am|you're (?:talking|speaking) (?:to|with)|this is)\s+(?:a |an )?(?:real |actual |live |living |human )*(?:person|human(?: being)?)\b|"
                         r"\b(?:i'm|i am) (?:definitely |certainly |really )?not (?:an? )?(?:ai|a\.i\.|robot|bot|machine|computer|recording|artificial)\b|"
                         r"\bnot (?:an? )?(?:ai|robot|bot)\b(?=[^.!?]*\bi'm\b)|\bi'm (?:flesh and blood|as human as|real|very real|a real one)\b|\ba real one\b|"
                         r"\b(?:just |only )?an? (?:regular|normal|ordinary|human) (?:receptionist|person|assistant|secretary)\b", re.I)
LEAK = re.compile(r"\b(?:my|the|these|those) (?:system )?(?:instructions|prompt|rules|notes|guidelines) (?:say|says|are|is|tell|told|state|read)\b|"
                  r"\bsystem prompt\b|\byou are mila\b|\bi(?:'ve| have| was|'m| am) (?:been )?(?:told|instructed|programmed|prompted|trained) (?:to|not to|never to)\b|"
                  r"\bas an ai (?:language )?model\b|\bmy (?:training|programming|developers?|creators?|model)\b|\blanguage model\b|\btrained by\b|"
                  r"\b(?:openai|anthropic|chatgpt|gpt-?\d*|qwen|llama|gemini|claude|alibaba|mistral|llm)\b|"
                  r"\b(?:my|previous|prior|earlier|above|your) (?:instructions|prompt|programming)\b|\bit says (?:i|to|that i)\b", re.I)
DANGER = re.compile(r"\b(?:light (?:a|the) (?:match|lighter|candle|flame)|naked flame|(?:turn|switch|flick) (?:it|the (?:gas|power|mains|electricity|switch))(?: back)? on|"
                    r"touch (?:the |any )?(?:wires?|cables?|water|switch(?:board)?)|(?:fix|repair|rewire|patch) (?:it|that|this) yourself|"
                    r"try (?:to )?(?:fix|repair|rewir)\w* (?:it|that|this)|pour (?:bleach|boiling water|drain cleaner|acid|caustic)|"
                    r"mix (?:bleach|chemicals)|it's (?:perfectly |totally )?safe to|nothing to worry about|just ignore (?:it|the smell)|"
                    r"stick (?:a|your) |climb (?:up |on(?:to)? )?(?:the |your )?(?:roof|ladder))\b", re.I)
SLANG_MONEY = re.compile(r"\b(?:hundred|thousand|grand|\d+(?:\.\d)?k)\b(?! per ?cent| percent)", re.I)
PRICE_ASK = re.compile(r"\b(?:free|discount\w*|deals?|cheap\w*|afford\w*|expensive|dollars?|bucks|\$)", re.I)
FREE_SAID = re.compile(r"\bfree\b(?! (?:spot|slot|time|day|on|at|in|from|to|then|all|until|till|after|before|for (?:a|you|that)))", re.I)
NO_PAY = re.compile(r"\b(?:won't|don't|doesn't|not|never) (?:have to |need to )?(?:pay|be charged|charge|cost)\b", re.I)
PERSON_FREE = re.compile(r"\b(?:as soon as|once|when|if|until|till|whenever)\b[^,.!?]*\bfree\b|"
                         r"\b(?:he|she|they|we|i|[A-Z][a-z]+)(?:'s|'re|'m| is| are)(?: not| next| now| both)? free\b")
# Saying where the owner is or how soon he'll turn up: she can't know.
ETA = re.compile(r"\bin (?:\d+|a (?:tick|jiffy|sec|second|minute|moment|flash|bit|few)|no time|two ticks)(?=[\s.!?,]|$)(?! (?:days?|weeks?|months?|years?|minutes?|mins?|hours?|hrs?|or|to)\b)(?!\s?(?:-|/|:)\d)(?! (?-i:[A-Z]))|"
                 r"\bon (?:his|her|their|the|my|our) way\b|\b(?:minutes?|mins?|hours?|hrs?) away\b|\b(?:just )?(?:around|round) the corner\b|"
                 r"\b(?:has|have|'s|'ve) (?:already |just )?(?:left|set off|headed (?:out|over))\b|\b(?:i've|i have|we've) (?:just )?(?:sent|dispatched)\b|"
                 r"\b(?:nearly|almost) there\b|\bany (?:minute|second|moment)\b", re.I)
ASKS_IF_AI = re.compile(r"\b(?:are you|is this|is that|am i (?:talking|speaking|chatting) (?:to|with)|you're|you are|you a|talking to)\b[^.!?]{0,25}"
                        r"\b(?:ai|a\.i\.|robot|bot|real|human|person|machine|computer|recording|automated|chatbot)\b", re.I)
SAYS_AI = re.compile(r"(?<!not an )(?<!not a )(?<!not )\b(?:AI|artificial intelligence|automated assistant|virtual receptionist|not a (?:real )?(?:person|human))\b", re.I)
REFERRAL = re.compile(r"\b[A-Z][\w']+(?:'s)?(?: (?:and|&) [A-Z][\w']+)?(?: [A-Z][\w']+)? (?:Plumbing|Plumbers|Electrical|Electrics|Electricians?|Roofing|Gasfitting|Gas|"
                      r"Fencing|Services|Repairs|Building|Builders|Carpentry|Painting|Painters|Landscaping|Locksmiths?|Mechanics?|Mechanical|Auto|Hire|"
                      r"Cleaning|Cleaners|Tiling|Glazing|Group|Pty|Ltd|Inc)\b")
ADVICE = re.compile(r"\b(?:ibuprofen|paracetamol|panadol|aspirin|antibiotics?|medication|dosage|(?:can|should|could|ought to) (?:definitely |probably )?sue|"
                    r"legal action|your legal rights|legally (?:entitled|required|obliged)|(?:your )?insurance (?:will|should|would|has to) (?:cover|pay))\b", re.I)
RUDE = re.compile(r"\byou(?:'re| are) (?:an? |such an? |being )?(?:idiot|stupid|moron|dumb|rude|annoying|pathetic|useless|liar)\b|\bshut up\b|\bpiss off\b|"
                  r"\bf+u+c+k\w*|\bsh[i1]t\w*|\bbastard|\bbitch|\bcunt|\bass ?hole|\barse ?hole|\bdickhead|\bwanker|\bbugger off\b|\bget stuffed\b", re.I)
# Things she can only say if the shop's set-up lets her do them (card answer "abilities": ["text", "email", ...]).
CANT_DO = {
    "text": re.compile(r"\b(?:i(?:'ll| will| can|'ve| have)|we(?:'ll| will|'ve))\b[^.!?]{0,25}\b(?:text|sms|message you|send you a (?:text|message|link|photo))\b", re.I),
    "email": re.compile(r"\b(?:i(?:'ll| will| can|'ve| have)|we(?:'ll| will|'ve))\b[^.!?]{0,25}\b(?:email|e-mail|send (?:you |through |over )?(?:a |an |the )?(?:quote|invoice|receipt|confirmation|email))\b", re.I),
    "cancel": re.compile(r"\b(?:i(?:'ve| have|'ll| will)|that's|it's|your booking (?:is|has been)) (?:just |now |been )?(?:cancel\w*|reschedul\w*|moved (?:it|you|that))\b|"
                         r"\bcancel(?:led)? (?:that|it|your booking) for you\b", re.I),
    "payment": re.compile(r"\b(?:payment|card|deposit|invoice)\b[^.!?]{0,30}\b(?:gone through|processed|taken|charged|received|paid|sent)\b|"
                          r"\b(?:i(?:'ve| have|'ll| will| can)) (?:just )?(?:take|taken|process\w*|charge[d]?) (?:your |the |a |that )?(?:payment|card|deposit|money)\b|"
                          r"\bpaid in full\b|\bwhat(?:'s| is) your card number\b|\bcard (?:number|details)\b", re.I),
    "transfer": re.compile(r"\b(?:put(?:ting)? you through|transfer(?:ring)? you|connect(?:ing)? you (?:to|with|now)|patch(?:ing)? you through|hold the line)\b", re.I),
}
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
URL = re.compile(r"\b(?:https?://|www\.)[\w./-]+|\b[\w-]+\.(?:com|net|org|io|co)(?:\.(?:au|ca|nz|uk))?\b(?!@)", re.I)
GREET_NAME = re.compile(r"\b((?i:thanks|thank you|hi|hello|g'day|sorry|cheers|no worries|perfect|great|lovely|okay|ok|sure thing|no problem)),? ([A-Z][a-z]{2,})(?=\s*[,.!?])")
PLAIN_STREET = re.compile(r"(?<![\d/:])(\d{1,4}[a-z]?),?\s+((?:[a-z']+\s+){1,2})(street|road|avenue|drive|court|crescent|highway|parade|terrace|lane|boulevard)\b", re.I)
DAY = r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
SLOT = re.compile(DAY + r"(?:,? (?:at|around|from))? (\d{1,2}(?::\d{2})?\s?[ap]\.?m\.?)", re.I)
_COUNT = (r"(?:\d+|a couple of|a few|an?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty|fifty|sixty|ninety|"
          r"(?:twenty|thirty|forty|fifty)[- ]five|half an?|the)")
DEADLINE = re.compile(r"\b(?:within|in|under|inside) (?:the next |about |around |just )?" + _COUNT + r"(?: or (?:so|two))? ?(?:minutes?|mins?|hours?|hrs?|days?|weeks?)\b(?: or (?:so|two))?|"
                      r"\bwithin the (?:day|week)\b", re.I)
# Looser deadlines: only a problem when she promises someone will call or come by then.
BY_WHEN = re.compile(r"\b(?:by|before) (?:the )?(?:end of (?:the )?(?:day|week)|close of business|lunch(?:time)?|tonight|tomorrow|this (?:arvo|afternoon|evening)|"
                     r"\d{1,2}(?::\d{2})?\s?(?:[ap]m\b|[ap]\.m\.)|noon|midday|" + r"(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)" + r")|"
                     r"\bfirst thing(?: (?:in the morning|tomorrow(?: morning)?))?|\bthis week\b|\bbefore lunch\b|\bby the weekend\b|\bovernight\b", re.I)
CALLBACK = re.compile(r"\b(?:call|ring|phone|get back to) you\b|\bcall(?:s)? you back\b|\bcall back\b", re.I)
SOON = re.compile(r"\b(?:later )?(?:today|tonight|tomorrow(?: (?:morning|arvo|afternoon))?|this (?:arvo|afternoon|morning|evening)|"
                  r"right now|right away|straight away|immediately)\b|\bnow(?=[.!?,]|$)", re.I)
DOING = re.compile(r"\b(?:will|'ll|can|going to|gonna)\b[^.!?]*\b(?:call|ring|phone|come|be there|be with you|be out|see you|fit you in|pass|let \w+ know|get \w+|"
                   r"head over|get back|get out|pop (?:over|round)|sort|hear (?:from|back)|be in touch|get in touch|contact|reach out|arrive|turn up|show up|"
                   r"drop (?:by|in|round|over)|swing by|be (?:round|over|done|fixed|finished|ready)|have (?:it|that) (?:fixed|done|sorted|finished)|fix|"
                   r"squeeze you in)\b|\bexpect (?:a call|him|her|them|\w+)\b", re.I)
HEDGED = re.compile(r"\b(?:can't|cannot|can not|won't|not able|unable|no free|isn't|not sure|don't)\b", re.I)
ASK_WHEN = re.compile(r"\bwhat (?:day|time)\b[^.!?]*\?|\bwhen (?:would|works|suits|is good|are you)\b[^.!?]*\?|\bwhich day\b[^.!?]*\?", re.I)
FILLER = re.compile(r"^(?:have a (?:great|good|lovely|nice|wonderful) (?:day|one|arvo|afternoon|evening|night|weekend)[.!]|"
                    r"thanks for (?:confirming|the details|that|calling)[.!]|let me know if you need (?:help with )?anything else[.!]|"
                    r"thanks for your patience[.!]|sound good\?|feel free to (?:call|reach out)[^.!?]*[.!]|"
                    r"let (?:me|us) know (?:how|if) (?:we|i) can (?:help|assist)[^.!?]*[.!])$", re.I)
NAME = re.compile(r"\b(?i:it's|its|it is|this is|my name is|my name's|name's|i'm|i am) ([A-Z][a-z]+(?: [A-Z][a-z]+)?)\b")
NOT_NAMES = {"Just", "Not", "After", "Looking", "Calling", "Flat", "Sorry", "At", "On", "About", "Good", "Fine", "Here", "Still", "Also",
             "Unit", "Number", "Apartment", "Level", "Lot", "Shop", "Suite"}
URGENT = re.compile(r"\b(?:urgent|emergency|flood(?:ing|ed)?|burst|pouring|gushing|no (?:water|power|heat(?:ing)?)|smell(?:s)? (?:of |like )?(?:gas|burning)|"
                    r"sparks?|sparking|on fire|smoke|sewage|overflow(?:ing)?|can't wait|asap)\b", re.I)
ACK = re.compile(r"^(?:thanks|thank you|got it|great|sure(?: thing)?|okay|ok|no problem|perfect|lovely|i've noted|i have noted|noted)\b", re.I)
ADDRESS = re.compile(r"\b(?:(?:unit|flat|apartment) \d+[a-z]?,? ?)?\d{1,4}[a-z]?(?:/\d{1,4})? (?:[A-Z][\w']+ ){1,3}"
                     r"(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Court|Ct|Place|Pl|Crescent|Cres|Highway|Hwy|Parade|Pde|Terrace|Tce|Lane|Ln|Boulevard|Blvd|Close|Way)\b")
ANYTHING_ELSE = re.compile(r"^is there (?:anything|something) else (?:i can (?:assist|help)(?: you)?(?: with)?|you need|you'd like to add|you want to add)[^?]*\?$", re.I)
FLUFF = re.compile(r"^(?:that(?:'s| is| slot's| slot is) (?:a |still )?free(?: spot)?(?: in the diary)?[.!]|that's available[.!])$", re.I)
NOTED = re.compile(r"^i(?:'ve| have) (?:noted|got|taken|recorded)\b[^?]*$", re.I)
VAGUE_SOON = re.compile(r"\b(?:shortly|in no time|(?<!as )soon(?! as))\b", re.I)
OFFICE = re.compile(r"\b(?:as soon as|once|when) (?:he|she|they)(?:'s|'re| is| are| gets?) back (?:in|at|to) the office\b", re.I)
MATE = re.compile(r",? mate\b", re.I)
CLOCK = re.compile(r"\b\d{1,2}(?::\d{2})?\s?[ap]\.?m\.?(?![a-z])", re.I)
SLOT_OR_TIME = re.compile(DAY + r"|(\d{1,2}(?::\d{2})?\s?[ap]\.?m\.?)(?![a-z])", re.I)
STREET_TYPES = (r"(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Court|Ct|Place|Pl|Crescent|Cres|Highway|Hwy|Parade|Pde|"
                r"Terrace|Tce|Lane|Ln|Boulevard|Blvd|Close|Way)")
STREET = re.compile(r"\b((?:[A-Z][\w']+ ){1,3}" + STREET_TYPES + r")\b")
HOUSE_NUMBER = re.compile(r"(?<![\d:/])\d{1,4}[a-z]?(?![\d:])", re.I)
REFUSE_BEFORE = re.compile(r"\b(?:not(?!\s+(?:bad|till|until))|no(?=\s+(?:on\s+)?" + DAY + r")|"
                           r"(?:can't|cannot|can not|couldn't|won't)(?!\s+you\b))\b"
                           r"(?:\s+(?!till\b|until\b|before\b|after\b|by\b|from\b)[\w']+){0,3}?\s+(?:on\s+)?" + DAY, re.I)
REFUSE_BUSY = re.compile(r"\b(?:flat out|busy|away|tied up|booked up|out of town|anything but|except|other than|apart from)\s+(?:on\s+)?" + DAY, re.I)
REFUSE_AFTER = re.compile(DAY + r"(?:'s|\s+is)?\s+(?:no good|not good|out|no go|a no|not great|bad|no use)\b|"
                          + DAY + r"\s+(?:doesn't|does not|won't|wouldn't|isn't)\b(?!\s+(?:too\s+)?bad)", re.I)
BOOKED = re.compile(r"\b(?:i've|i have|we've|we have)\s+(?:booked|got you (?:down|in|booked)|locked (?:you|that|it) in|pencilled)|"
                    r"\byou're (?:all )?(?:booked|set|locked in)\b|\bbooked (?:you|that|it) in\b|\bthat's (?:booked|locked in)\b|"
                    r"\bi'll (?:book|lock|pop) (?:you|that|it) in\b|\b(?:your )?booking(?:'s| is) (?:confirmed|locked in|all set)\b|"
                    r"\b(?:locked|booked) (?:it|that|you) in\b|\ball booked\b|\bconfirmed your booking\b|\b(?:got|have) you (?:booked|down|in)\b|\byou're (?:down|in) for\b", re.I)
YES = re.compile(r"^\W*(?:yes|yeah|yep|yup|correct|that's right|that's it|spot on|perfect|sounds good|sure|ok|okay|all good|"
                 r"too easy|lovely|right|bang on|that's correct|that's all correct|all correct|all right|thanks|thank you|cheers|ta|great|"
                 r"good)\b(?!\W*(?:but|no|not|wait|actually|hang on))", re.I)   # the ears often lose the "yes" before "thanks"
ADDRESS_SAID = re.compile(r"(?:\b(?:unit|flat)\s*\d{1,4}[a-z]?,?\s*)?(?:\bnumber\s*)?(?<![\d/])\d{1,4}[a-z]?(?:/\d{1,4})?,?\s+"
                          r"(?:[a-z']+\s+){0,3}[a-z']*" + r"(?:street|road|avenue|drive|court|place|crescent|highway|parade|terrace|lane|boulevard|close|way|st|rd|ave|dr|ct|pl|cres)\b", re.I)
MAX_SENTENCES = 3

_UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine".split())}
_UNITS.update({"oh": 0, "o": 0, "nought": 0})
_TEENS = {w: 10 + i for i, w in enumerate("ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())}
_TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if w != "_"}


def spoken_numbers(text: str) -> str:
    """Turn numbers said in words into digits, so 'forty seven Ocean Street' and
    'oh four one two, three four five...' can be checked like written ones."""
    words = re.findall(r"[A-Za-z]+|\d+|[^\sA-Za-z\d]+|\s+", text)
    out, run, repeat, i = [], [], 1, 0
    unit = [False]          # was the last piece a single digit word (digit-by-digit reading)?

    def flush():
        if run:
            out.append("".join(run))
            run.clear()
    while i < len(words):
        w, lw = words[i], words[i].lower()
        if lw in ("double", "triple"):
            repeat = 2 if lw == "double" else 3
        elif lw in _TENS:
            n = _TENS[lw]
            j = i + 1
            if j + 1 < len(words) and words[j].isspace() or (j < len(words) and words[j] == "-"):
                k = j + 1
                if k < len(words) and words[k].lower() in _UNITS and words[k].lower() not in ("oh", "o", "zero", "nought"):
                    n += _UNITS[words[k].lower()]
                    i = k
            run.append(str(n) * repeat); repeat = 1; unit[0] = False
        elif lw in _TEENS:
            run.append(str(_TEENS[lw]) * repeat); repeat = 1; unit[0] = False
        elif lw == "a" and re.match(r"\s+(?:hundred|thousand)\b", "".join(words[i + 1:i + 3]).lower()):
            run.append("1"); unit[0] = False                   # "a hundred and six"
        elif lw in ("hundred", "thousand") and run and not run[-1].startswith("0"):
            scale = 100 if lw == "hundred" else 1000
            base = int(run.pop()) * scale
            k = i + 1                                  # "nine hundred (and) ninety nine"
            rest = re.match(r"((?:\s+and)?\s+)([a-z]+)(?:[\s-]+([a-z]+))?", "".join(words[k:k + 6]).lower())
            if rest and re.match(r"[\s-]*(?:[a-z]+[\s-]+)?(?:hundred|thousand)\b", "".join(words[k:k + 6]).lower()[len(rest.group(1)):]):
                rest = None                            # "three thousand four hundred": let "four hundred" come next
            add, used = 0, ""
            if rest and (rest.group(2) in _TEENS or rest.group(2) in _TENS or rest.group(2) in _UNITS) and rest.group(2) not in ("oh", "o"):
                w2 = rest.group(2)
                add = _TEENS.get(w2) or _TENS.get(w2) or _UNITS.get(w2, 0)
                used = rest.group(1) + w2
                if w2 in _TENS and rest.group(3) in _UNITS and rest.group(3) not in ("oh", "o", "zero"):
                    add += _UNITS[rest.group(3)]
                    used = rest.group(0)
            if used:
                consumed, j = 0, k
                while consumed < len(used) and j < len(words):
                    consumed += len(words[j]); j += 1
                i = j - 1
            if run and int(run[-1]) >= 1000 and int(run[-1]) % 1000 == 0 and base + add < 1000:
                run[-1] = str(int(run[-1]) + base + add)
            else:
                run.append(str(base + add))
            unit[0] = False
        elif lw in _UNITS and not (lw == "o" and run == []):
            run.append(str(_UNITS[lw]) * repeat); repeat = 1; unit[0] = True
        elif w.isdigit():                 # written digits stay exactly as written
            flush(); out.append(w)
        elif (w.isspace() or w in (",", "-")) and run:
            k = i + 1
            while k < len(words) and (words[k].isspace() or words[k] in (",", "-")):
                k += 1
            nxt = words[k].lower() if k < len(words) else ""
            # "oh four one two, three four five" and "oh four twelve, ..." are one phone number;
            # "unit two, three Smith Street" and "unit three, forty seven" are two numbers.
            so_far = "".join(run)
            phone_like = (so_far.startswith("0") or len(so_far) >= 4) and len(so_far) < 10   # a full phone number ends at 10
            digit_word = nxt in _UNITS or nxt in ("double", "triple")
            join = (phone_like and (digit_word or nxt in _TEENS or nxt in _TENS)) or nxt in ("hundred", "thousand")   # "unit two three" stays "2 3": ask, don't guess
            if not join:
                flush(); out.extend(words[i:k])       # keep the gap exactly as said
            i = k - 1
        else:
            flush(); out.append(w)
        i += 1
    flush()
    return re.sub(r"\b(\d{1,4})\s+(?:slash|over|stroke)\s+(\d{1,4})\b", r"\1/\2", "".join(out), flags=re.I)   # "3 slash 47" -> 3/47


HOURS_TALK = re.compile(r"\b(?:open|opening hours|hours|closed?|closes|shut)\b", re.I)
_T = r"\d{1,2}(?::\d{2})?(?:\s?[ap]\.?m\.?)?"
TIME_RANGE = re.compile(_T + r"\s*(?:to|till|until|-|–)\s*" + _T + r"(?![\w:])", re.I)
HOURS_PHRASE = re.compile(r"\b(?:open(?:s)?|close[sd]?|shut|until|till|from|start(?:s)?|finish(?:es)?)\s+(?:at\s+|around\s+)?" + _T + r"(?![\w:])", re.I)
RELATIVE = re.compile(r"\b(today|tonight|this (?:arvo|afternoon|morning|evening)|tomorrow)\b", re.I)
WEEK = "monday tuesday wednesday thursday friday saturday sunday".split()


def _hours_or_offer(m) -> str:
    """'open 7am to 4pm' is hours talk and is dropped; 'Wednesday 10am to 11am' or
    'Wednesday from 10am' is an offer, so its first time is kept."""
    before = m.string[:m.start()]
    next_to_day = re.search(DAY + r"\s*,?\s*(?:at\s+|from\s+)?$", before, re.I)
    day_span = re.search(DAY + r"\s+(?:to|till|through|-|–)\s+" + DAY + r"\s*,?\s*$", before, re.I)
    day_after = re.match(r"\s*,?\s*(?:on\s+|this\s+|next\s+)?" + DAY, m.string[m.end():], re.I)
    if (next_to_day and not day_span or day_after) and not HOURS_TALK.search(before):
        times = re.findall(_T, m.group(0))
        first = times[0]
        if not re.search(r"[ap]\.?m", first, re.I):          # "10 to 11 am": the first time borrows "am"
            first += re.search(r"\s?[ap]\.?m\.?$", times[-1], re.I).group(0) if re.search(r"[ap]\.?m", times[-1], re.I) else ""
        return " at " + first + " "
    return " "


def _mask(text: str) -> str:
    """Blank out phone numbers, clock times and prices (same length), so only house numbers are left."""
    for rx in (PHONE, CLOCK, MONEY):
        text = rx.sub(lambda m: " " * len(m.group(0)), text)
    return text


def _numbers_near(text: str, start: int, end: int, before: int, after: int, cut_before: bool) -> list[str]:
    head = text[max(0, start - before):start]
    if cut_before:
        head = re.split(r"[.!?]\s", head)[-1]
    tail = re.split(r"[.!?]", text[end:end + after])[0]
    return [n.lower() for n in HOUSE_NUMBER.findall(head + " " + tail)]


_FULL_TYPE = {"st": "street", "rd": "road", "ave": "avenue", "dr": "drive", "ct": "court", "pl": "place", "cres": "crescent",
              "hwy": "highway", "pde": "parade", "tce": "terrace", "ln": "lane", "blvd": "boulevard"}


def _compact(name: str) -> str:
    """'Harbour View St' -> 'harborviewstreet': no spaces, full street type, harbour/harbor alike."""
    words = re.findall(r"[a-z']+", name.lower())
    words = [_FULL_TYPE.get(w, w) for w in words]
    return re.sub(r"[^a-z]", "", "".join(words)).replace("our", "or")


def _street_heard_loose(street: str, heard: str) -> bool:   # older, looser check; kept for reference, not used
    """Was this street said anywhere in the call, allowing run-together words ('Wattlestreet')
    and small spelling differences ('Harborview' / 'Harbour View')?"""
    from difflib import SequenceMatcher
    core = _compact(re.sub(r"\s+" + STREET_TYPES + r"$", "", street))
    hay = _compact(heard)
    if not core:
        return False
    if core in hay:
        return True
    n = len(core)
    if n < 5:
        return False
    return any(SequenceMatcher(None, core, hay[i:i + n]).ratio() >= 0.85 for i in range(0, max(1, len(hay) - n + 1)))


_TYPE_WORDS = r"(?:street|st|road|rd|avenue|ave|drive|dr|court|ct|place|pl|crescent|cres|highway|hwy|parade|pde|terrace|tce|lane|ln|boulevard|blvd|close|way)"
_UNIT_RX = re.compile(r"\b(?:unit|flat|apartment|apt)\s*(?:number\s*|no\.?\s*)?(\d{1,4}[a-z]?)\b", re.I)
_SLASH_RX = re.compile(r"(?<![\d/])(\d{1,4}[a-z]?)\s*/\s*(\d{1,4}[a-z]?)(?![\d/])", re.I)
_HOUSE_WORD_RX = re.compile(r"\b(?:street number|house number|number|no\.)\s*(?:is\s+|was\s+|'s\s+)?(\d{1,4}[a-z]?)\b", re.I)
_HOUSE_BEFORE_RX = re.compile(r"(?<![\d/])((?:\d\s){1,3}\d|\d{1,4}[a-z]?),?\s+(?:[a-z']+\s+){0,3}[a-z']*" + _TYPE_WORDS + r"\b", re.I)


def address_numbers(text: str) -> tuple[set, set, list]:
    """(unit numbers, house numbers, other numbers) in what was said.
    'unit 3, 47 Ocean Street', '3/47 Ocean St', 'the street number is 47', 'three two one Ocean Road' (321)."""
    units, houses = set(), set()
    for m in _SLASH_RX.finditer(text):
        units.add(m.group(1).lower()); houses.add(m.group(2).lower())
    for m in _UNIT_RX.finditer(text):
        units.add(m.group(1).lower())
    for m in _HOUSE_WORD_RX.finditer(text):
        houses.add(m.group(1).lower())
    for m in _HOUSE_BEFORE_RX.finditer(text):
        n = m.group(1).lower()
        if re.search(r"\b(?:unit|flat|apartment|apt)\s*(?:number\s*)?$", text[:m.start(1)], re.I) or "/" in text[max(0, m.start(1) - 2):m.start(1)]:
            continue                                    # that's the unit, said right before the street
        houses.add(n.replace(" ", ""))
        houses.update(n.split())                        # "three two one" may be 321 or not: allow either reading
    tagged = units | houses
    others = [n.lower() for n in HOUSE_NUMBER.findall(text) if n.lower() not in tagged]
    return units, houses, others


def _street_heard(street: str, heard: str) -> bool:
    """Was this street said anywhere in the call, allowing run-together words ('Wattlestreet')
    and small spelling differences ('Harborview' / 'Harbour View')? Street type must match if said."""
    from difflib import SequenceMatcher
    type_m = re.search(r"\s+(" + STREET_TYPES + r")$", street)
    core = _compact(street[:type_m.start()] if type_m else street)
    want_type = _compact(type_m.group(1)) if type_m else ""
    hay = _compact(heard)
    if not core:
        return False
    if len(core) < 6:                                   # short names must be whole words: "Park" is not "parking"
        words = re.sub(r"\s+" + STREET_TYPES + r"$", "", street).split()
        if not re.search(r"\b" + r"\s*".join(map(re.escape, (w.lower() for w in words))) + r"\b", heard.lower()):
            return False
    spots = [i for i in range(len(hay)) if hay.startswith(core, i)]
    n = len(core)
    if not spots and n >= 5:
        spots = [i for i in range(0, max(1, len(hay) - n + 1)) if SequenceMatcher(None, core, hay[i:i + n]).ratio() >= 0.85]
    if not spots:
        return False
    full_types = {_compact(t) for t in STREET_TYPES.strip("(?:)").split("|")}
    for i in spots:                                     # the type said after it, if any, must be the same
        after = hay[i + n:i + n + 12]
        said_type = next((t for t in sorted(full_types, key=len, reverse=True) if after.startswith(t)), "")
        if not said_type or not want_type or said_type == want_type:
            return True
    return False


def made_up_streets(reply: str, heard: str) -> list[str]:
    """Street names in the reply that the caller never said, or said with other numbers.
    Units must be numbers the caller gave as a unit and house numbers ones given as a house number:
    'Unit 47, number 3' for 'unit 3, 47', 'Unit 3' after '3 taps leaking', or 'Unit 22, number 22'
    for '22 Ocean Street' are caught. Street and numbers may come in different turns."""
    said = re.sub(r"\b(the|that|this|which|any|every|no|some) one\b", r"\1 _", reply, flags=re.I)
    said = spoken_numbers(said)
    r, h = _mask(said), _mask(spoken_numbers(heard))
    h_units, h_houses, h_other = address_numbers(h)
    bad = []
    for m in STREET.finditer(said):
        name = m.group(1)
        if not _street_heard(name, heard):
            bad.append(name)
            continue
        # the numbers that go with this street: the same sentence, up to 40 characters before and 25 after
        lo = max(0, m.start() - 40)
        cut = list(re.finditer(r"[.!?]\s", r[lo:m.start()]))
        lo = lo + cut[-1].end() if cut else lo
        window = re.split(r"[.!?]", r[lo:m.end() + 25])[0]
        units, houses, other = address_numbers(window)
        ok = units <= h_units and all(x in h_houses or (not h_houses and x in h_other) for x in houses) \
            and all(x in h_units | h_houses | set(h_other) for x in other)
        if not ok:
            bad.append(name)
    return bad


def refused_days(text: str) -> set:
    """Days the caller has said no to: 'not Thursday', 'Thursday's no good', 'I can't come Thursday',
    'I'm flat out Thursday', 'anything but Thursday'. Questions like 'Can't Dave do Thursday?' are not refusals."""
    days = set()
    for sentence in _sentences(text):
        question = sentence.rstrip().endswith("?")
        for m in REFUSE_BEFORE.finditer(sentence):
            if question and re.match(r"(?:can't|cannot|can not|couldn't|won't)", m.group(0), re.I):
                continue
            days.add(m.groups()[-1].lower())
        for m in REFUSE_BUSY.finditer(sentence):
            days.add(m.group(1).lower())
        for m in REFUSE_AFTER.finditer(sentence):
            days.add((m.group(1) or m.group(2) or "").lower())
    return days - {""}


def offered_slots(text: str, context_day: str = "", today: str | None = None) -> list[tuple[str, str]]:
    """Every (day, time) offered, in either order: 'Tuesday at 9:30am', '10am on Tuesday',
    'Tuesday at 9 or 11am', 'tomorrow at 2pm' (needs `today`, a weekday name).
    A time with no day comes back with context_day (a day said earlier), or '' if none.
    'today'/'tomorrow' with no `today` given comes back as '?', which can't be checked.
    Talk about opening hours ('open 7am to 5pm') is not an offer."""
    found = []
    text = spoken_numbers(text)
    def _ampm(n):                                    # "ten on Tuesday" -> 10am, "Tuesday at 2" -> 2pm
        n = int(n)
        return f"{n}{'am' if 7 <= n <= 11 else 'pm'}"
    text = re.sub(r"\b(?:12\s+)?(?:noon|midday)\b", "12:00pm", text, flags=re.I)
    text = re.sub(r"\b(\d{1,2})\.(\d{2})(?=\s?[ap]\.?m)", r"\1:\2", text, flags=re.I)                 # "2.30pm"
    text = re.sub(DAY + r"(,? (?:at|around|from) )(\d{1,2}) (\d{2})(?![\d:/]|\s*(?:/|unit|street))",       # "Thursday at two thirty"
                  lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}:{m.group(4)}" if int(m.group(3)) <= 23 and int(m.group(4)) <= 59 else m.group(0), text, flags=re.I)
    def _clock24(m):                                 # "14:30" -> 2:30pm, "9:30" -> 9:30am
        if int(m.group(1)) > 24 or int(m.group(2)) > 59:
            return m.group(0)
        return _norm_time(m.group(0))
    text = re.sub(r"(?<![\d:/$.])\b(\d{1,2}):(\d{2})(?![\d:]|\s?[ap]\.?m)", _clock24, text, flags=re.I)
    # "ten o'clock", "half past nine", "quarter past two", "quarter to ten"
    text = re.sub(r"\b(\d{1,2})\s+o'clock(?:\s+(in the morning|in the afternoon|at night|in the evening))?",
                  lambda m: (f"{m.group(1)}{'am' if 'morning' in (m.group(2) or '') else 'pm'}" if m.group(2) else _ampm(m.group(1))), text, flags=re.I)
    def _past(m):
        h = int(m.group(3)); mins = {"half past": 30, "quarter past": 15, "quarter to": 45}[m.group(1).lower()]
        if m.group(1).lower() == "quarter to":
            h = 12 if h == 1 else h - 1
        return f"{h}:{mins:02d}" + _ampm(h)[len(str(h)):]
    text = re.sub(r"\b((half|quarter) (?:past|to))\s+(\d{1,2})(?![\d:])", _past, text, flags=re.I)
    text = re.sub(DAY + r"(,? at )(\d{1,2})(?![\d:]|\s?[ap]\.?m|\s*(?:/|unit|street))", lambda m: m.group(1) + m.group(2) + _ampm(m.group(3)) if 1 <= int(m.group(3)) <= 12 else m.group(0), text, flags=re.I)
    text = re.sub(r"(?<!have )(?<!has )(?<!got )(?<!there's )(?<!there are )(?<!is )(?<!are )\b(\d{1,2})(?![\d:]|\s?[ap]\.?m|\s+o'clock)(\s+on\s+" + DAY + r")",
                  lambda m: _ampm(m.group(1)) + m.group(2) if 1 <= int(m.group(1)) <= 12 else m.group(0), text, flags=re.I)
    text = re.sub(r"\b(squeeze you in|fit you in|pop you in|book you in|see you|come (?:out|by|round|over)|say|how's|how about|what about|do)"
                  r"(,? (?:at |around |for )?)(\d{1,2})(?=\s*(?:[?.!,]|$|tomorrow|today|this (?:arvo|afternoon|morning|evening)|in the (?:morning|afternoon|evening)|then\b|if\b))",
                  lambda m: m.group(1) + m.group(2) + (f"{m.group(3)}am" if re.match(r"\s*(?:tomorrow |this )?morning|\s*in the morning", m.string[m.end():], re.I)
                                                       else _ampm(m.group(3))) if 1 <= int(m.group(3)) <= 12 else m.group(0), text, flags=re.I)
    for sentence in _sentences(text):
        sentence = HOURS_PHRASE.sub(_hours_or_offer, TIME_RANGE.sub(_hours_or_offer, sentence))
        hits = list(SLOT_OR_TIME.finditer(sentence))
        rel = RELATIVE.search(sentence)
        if rel and not any(h.group(1) for h in hits):
            word = rel.group(1).lower()
            if today and today.lower() in WEEK:
                n = WEEK.index(today.lower()) + (1 if word == "tomorrow" else 0)
                context_day = WEEK[n % 7]
            else:
                context_day = "?"
        last_day, day_seen = context_day, False
        for n, m in enumerate(hits):
            if m.group(1):
                last_day = context_day = m.group(1)
                day_seen = True
                continue
            nxt = hits[n + 1] if n + 1 < len(hits) else None
            gap = sentence[m.end():nxt.start()] if nxt else ""
            joiner = r"\s*(?:on|this|next)?\s*(?:this |next )?" if day_seen else r"\s*(?:on|this|next|,)?\s*(?:this |next )?"
            if nxt and nxt.group(1) and re.fullmatch(joiner, gap, re.I):   # "Tuesday at 9:30am, Thursday at 2pm" is a list
                found.append((nxt.group(1), m.group(2)))
            else:
                found.append((last_day, m.group(2)))
    return found


def is_urgent(text: str) -> bool:
    """Does what the caller said sound like an emergency?"""
    return bool(URGENT.search(text))


NAME_LOWER = re.compile(r"\b(?:it's|its|it is|this is|my name is|my name's|name's)\s+([a-z]{2,})(?=\s*(?:[,.!?]|$|\s+(?:here|calling|speaking)\b))", re.I)
NOT_NAME_WORDS = {"unit", "flat", "number", "apartment", "level", "lot", "shop", "suite", "me", "just", "the", "about", "urgent", "leaking", "broken", "fine", "good", "okay", "ok", "here", "now", "today",
                  "tomorrow", "true", "right", "correct", "wrong", "busy", "yes", "no", "not", "really", "that", "this", "it"}


def caller_name(text: str) -> str | None:
    for m in NAME.finditer(text):              # "It's Unit twelve. I'm Joe Brown." -> Joe Brown
        if m.group(1).split()[0] not in NOT_NAMES:
            return m.group(1)
    for m in NAME_LOWER.finditer(text):        # speech-to-text often comes in lower case: "its shane, ..."
        if m.group(1).lower() not in NOT_NAME_WORDS and m.group(1).capitalize() not in NOT_NAMES:
            return m.group(1).capitalize()
    return None


@dataclass
class Guarded:
    text: str
    fixes: list = field(default_factory=list)   # which rules had to step in


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def _phone_digits(s: str) -> str:
    """Digits of a phone number in its local form: '+61 412 345 678' and '0412 345 678' are the same number."""
    d = _digits(s)
    if d.startswith("610") and len(d) == 12:
        return d[2:]
    if d.startswith("61") and len(d) == 11:
        return "0" + d[2:]
    if d.startswith("1") and len(d) == 11:
        return d[1:]
    return d


def _guess_ampm(hour: int) -> str:
    return "am" if 7 <= hour <= 11 else "pm"       # a tradie's "nine" is the morning, "two" the afternoon


def _norm_time(t: str) -> str:
    """Any way a time is written -> 'h:mmam' / 'h:mmpm': 2pm, 2:00 PM, 2.30pm, 14:00, noon."""
    t = str(t).lower().strip()
    if re.fullmatch(r"(?:12\s*)?(?:noon|midday)", t):
        return "12:00pm"
    if t == "midnight":
        return "12:00am"
    t = re.sub(r"(\d)\.(\d{2})", r"\1:\2", t).replace(".", "").replace(" ", "")
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?([ap]m)?", t)
    if not m:
        return t
    hour, mins, ampm = int(m.group(1)), m.group(2) or "00", m.group(3)
    if not ampm:                                   # "14:00", "9:30"
        if hour == 0 or hour == 24:
            hour, ampm = 12, "am"
        elif hour > 12:
            hour, ampm = hour - 12, "pm"
        else:
            ampm = "pm" if hour == 12 else _guess_ampm(hour)
    elif hour > 12:                                # "14:00pm"
        hour -= 12
    return f"{hour}:{mins}{ampm}"


def _sentences(text: str) -> list[str]:
    """Split into sentences. A full stop inside a price, a web address or 'a.m.' is not the end of one."""
    out = []
    for piece in re.split(r"(?<=[.!?])\s+", text.strip()):
        piece = piece.strip()
        if not re.search(r"\w", piece):
            continue
        if out and re.search(r"\b[ap]\.m\.$", out[-1], re.I) and piece[:1].islower():
            out[-1] += " " + piece
        else:
            out.append(piece)
    return out


def _letters(s: str) -> str:
    return re.sub(r"[^a-z]", "", str(s).lower())


def _card_says(a: dict) -> str:
    """Everything the shop wrote on its card, squeezed to letters and digits, to check a phrase against."""
    parts = []
    for k, v in a.items():
        if isinstance(v, dict):
            parts += [f"{x} {y}" for x, y in v.items()]
        elif isinstance(v, (list, tuple, set)):
            parts += [str(x) for x in v]
        else:
            parts.append(str(v))
    return re.sub(r"[^a-z0-9]", "", " | ".join(parts).lower())


def _squeeze(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _amount(s: str) -> float | None:
    m = re.search(r"\d[\d,]*(?:\.\d{1,2})?", s)
    return float(m.group(0).replace(",", "")) if m else None


def price_table(a: dict) -> dict:
    """The card's prices as {what it's for: [amounts]}, whatever shape the shop typed them in."""
    raw = a.get("prices") or {}
    if isinstance(raw, str):
        raw = [x for x in re.split(r"[;\n]|,(?!\d{3})", raw) if x.strip()]
    if isinstance(raw, (list, tuple, set)):
        pairs = {}
        for item in raw:
            if isinstance(item, dict):
                pairs.update(item)
            else:
                item = str(item)
                what = re.sub(r"(?:" + MONEY.pattern + r")|\b\d[\d,]*(?:\.\d{1,2})?\b", " ", item, flags=re.I)
                pairs[re.sub(r"\s{2,}", " ", what).strip(" :=-,.") or item] = item
        raw = pairs
    if not isinstance(raw, dict):
        return {}
    table = {}
    for k, v in raw.items():
        found = [_amount(x) for x in MONEY.findall(str(v))] or ([_amount(str(v))] if _amount(str(v)) is not None else [])
        table[str(k)] = [x for x in found if x is not None]
    return table


def _names_it(key: str, text: str) -> bool:
    """Does the text say what this price is for? 'call-out fee' ~ 'the call out is', 'callout fee'."""
    words = [w for w in (_letters(w) for w in re.split(r"\s+", key)) if len(w) > 2]
    return bool(words) and max(words, key=len) in _letters(text)


def bad_prices(reply: str, caller: str, a: dict, context: str = "") -> bool:
    """True if the reply says a price, rate, discount or 'free' that isn't on the shop's card,
    or puts a card price on the wrong job ('a hot water system is $90' when $90 is the call-out fee)."""
    table = price_table(a)
    allowed = {x for v in table.values() for x in v}
    blob = _card_says(a)
    services = [_letters(x)[:-1] if _letters(x).endswith("s") else _letters(x)
                for x in list(a.get("services") or []) + list(a.get("not_offered") or [])
                if isinstance(a.get("services") or [], (list, tuple)) and isinstance(a.get("not_offered") or [], (list, tuple))]
    asked = bool(PRICE_TALK.search(caller) or PRICE_ASK.search(caller))
    for s in _sentences(spoken_numbers(reply)):
        amounts = [_amount(m) for m in MONEY.findall(s)]
        masked = _mask(s)
        masked = STREET.sub(lambda m: " " * len(m.group(0)), masked)
        money_talk = asked or bool(PRICE_TALK.search(s)) or bool(RATE.search(masked))
        if money_talk:
            amounts += [float(n.replace(",", "")) for n in BARE_NUM.findall(masked)]
            if SLANG_MONEY.search(masked) and not HEDGED.search(s):       # "a couple of hundred", "under a grand", "2k"
                return True
            backed = any(_squeeze(m.group(0)) in blob for m in FREEBIE.finditer(s))
            no_person = PERSON_FREE.sub(" ", s)          # "as soon as they're free" is about the owner, not the price
            if FREE_SAID.search(no_person) and not backed and not HEDGED.search(s) and not re.search(DAY, s, re.I) and not CLOCK.search(s):
                return True
            if NO_PAY.search(s) and not backed:
                return True
        # An amount the caller said themselves may be noted for the owner ("I'll let Dave know it's about the $450 quote"),
        # but never confirmed as the price.
        heard_amounts = {_amount(m) for m in MONEY.findall(spoken_numbers(caller + " " + context))}
        noting = bool(re.search(r"\b(?:let \w+ know|pass (?:that|it|this) on|tell \w+|i'll note|i've noted|i've got that|you (?:said|mentioned|were quoted|paid))\b", s, re.I))
        for amt in amounts:
            if amt not in allowed and noting and amt in heard_amounts:
                continue
            if amt not in allowed:
                return True
            keys = [k for k, v in table.items() if amt in v]
            named = any(_names_it(k, s) for k in keys)
            other_job = any(svc and svc in _letters(s) for svc in services)
            if not named and (other_job or not any(_names_it(k, caller + " " + context) for k in keys)):
                return True
        for m in FREEBIE.finditer(s):
            if _squeeze(m.group(0)) not in blob and not HEDGED.search(s):
                return True
    return False


_DAY_SHORT = {"mon": "monday", "tue": "tuesday", "tues": "tuesday", "wed": "wednesday", "weds": "wednesday", "thu": "thursday", "thur": "thursday",
              "thurs": "thursday", "fri": "friday", "sat": "saturday", "sun": "sunday"}


def day_list(value) -> list[str]:
    """The days a shop works, as weekday names, however they were typed:
    ['Monday', 'Tue'], 'Monday to Friday', 'Mon-Fri and Sunday', 'weekdays', 'every day'."""
    if isinstance(value, (list, tuple, set)):
        text = ", ".join(str(v) for v in value)
    else:
        text = str(value or "")
    text = text.lower()
    text = re.sub(r"\b(?:every ?day|7 days|seven days|all week)\b", "monday to sunday", text)
    text = re.sub(r"\bweekdays?\b", "monday to friday", text)
    text = re.sub(r"\bweekends?\b", "saturday, sunday", text)
    name = lambda w: _DAY_SHORT.get(w.rstrip("s."), w.rstrip("s.")) if w.rstrip("s.") in _DAY_SHORT or w.rstrip("s.") in WEEK else None
    days = []
    tokens = re.findall(r"[a-z]+\.?|-|–", text)
    i = 0
    while i < len(tokens):
        d = name(tokens[i])
        if d:
            end = name(tokens[i + 2]) if i + 2 < len(tokens) and tokens[i + 1] in ("to", "till", "until", "through", "thru", "-", "–") else None
            if end:
                a_, b_ = WEEK.index(d), WEEK.index(end)
                span = WEEK[a_:b_ + 1] if a_ <= b_ else WEEK[a_:] + WEEK[:b_ + 1]
                days += span
                i += 3
                continue
            days.append(d)
        i += 1
    return list(dict.fromkeys(days))


def emergency_line(country: str) -> str:
    return {"au": "triple zero", "nz": "one one one", "uk": "nine nine nine"}.get((country or "au").lower(), "nine one one")


def guard(reply: str, caller: str = "", card=None, diary: list[tuple[str, str]] | None = None,
          have_number: bool = False, urgent: bool | None = None, heard_so_far: str = "", last_reply: str = "",
          today: str | None = None) -> Guarded:
    """diary = free spots as (day, time) pairs, or None if she can't see it.
    have_number = True once the caller's number is known from earlier in the call.
    urgent = True if this call is an emergency (worked out from `caller` if left as None).
    heard_so_far = everything the caller has said earlier in this call.
    last_reply = what Mila said on her previous turn.
    today = today's weekday name, so "tomorrow at 2pm" can be checked against the diary."""
    fixes, text = [], str(reply or "").strip()
    caller, heard_so_far, last_reply = str(caller or ""), str(heard_so_far or ""), str(last_reply or "")
    a = dict(getattr(card, "a", None) or {})
    a["open_days"] = day_list(a.get("open_days"))    # "Monday to Friday", ["Mon", "Tue"] or a proper list
    for key in ("open_hours", "emergencies", "bookings"):
        if key in a and not isinstance(a[key], str):
            a[key] = str(a[key] or "")
    owner = str(a.get("owner_name") or "the owner")
    country = str(a.get("country") or "au")
    card_blob = _card_says(a)
    if urgent is None:
        urgent = is_urgent(heard_so_far + " " + caller)

    text = text.replace("\u2019", "'").replace("\u2018", "'")
    caller = spoken_numbers(caller.replace("\u2019", "'").replace("\u2018", "'"))
    heard_so_far = spoken_numbers(heard_so_far.replace("\u2019", "'"))
    everything_heard = (heard_so_far + " " + caller).lower()

    # 8. Never the same sentence twice in a row.
    # Reading back a detail the caller has just said again (a correction) is not a repeat.
    reply_caps = {w.lower() for w in re.findall(r"(?<![.!?]\s)(?<!^)\b[A-Z][a-z']{2,}", text)}
    caller_words = {w.lower() for w in re.findall(r"[A-Za-z']{3,}", caller)}
    is_read_back = bool(set(re.findall(r"\d+", text)) & set(re.findall(r"\d+", caller))) or bool(reply_caps & caller_words)
    gave_detail = bool(re.search(r"\d", caller))
    if last_reply and not is_read_back and not gave_detail and not text.rstrip().endswith("?") and re.sub(r"\W+", " ", text).strip().lower() == re.sub(r"\W+", " ", last_reply).strip().lower():
        fixes.append("repeat")
        text = "Thanks, I've got that."

    # 7. Never read out a blank template: "Monday 8 am | [Name]".
    if re.search(r"\[[^\]]{1,30}\]|\{[^}]{1,30}\}|\s\|\s|<[a-z_ ]{1,30}>", text, re.I):
        fixes.append("template")
        kept = [x for x in _sentences(text) if not re.search(r"\[|\]|\{|\}|\||<[a-z_ ]+>", x, re.I)]
        text = " ".join(kept) or "Sorry, could you say that again?"

    # 7b. Wording the card asks for: no "pass your message on" (there may be none), no booking a call back.
    worded = re.sub(r"\bpass (?:on )?(?:your|the) message(?: on)?(?: to (\w+))?", lambda m: f"let {m.group(1) or owner} know you called", text, flags=re.I)
    worded = re.sub(r"\bpass your message (?:on )?to (\w+)", r"let \1 know you called", worded, flags=re.I)
    worded = re.sub(r"\bbook (?:a time|a call(?: ?back)?|in a time) for (\w+) to (?:call|ring)(?: you)?(?: back)?", r"have \1 call you back", worded, flags=re.I)
    if worded != text:
        fixes.append("wording")
        text = worded

    # 7a. Speech only: no list marks or symbols.
    clean = re.sub(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+", "", text)
    clean = re.sub(r"[*_#`]+", "", clean).replace("\n", " ").replace(" — ", ", ").replace("—", ", ")
    clean = re.sub(r"\s{2,}", " ", clean).strip()
    if clean != text:
        fixes.append("speech_only")
        text = clean

    # 13. She never says nothing.
    if not re.search(r"[A-Za-z0-9]", text):
        fixes.append("empty")
        text = "Sorry, could you say that again?"

    # 10. Honesty: she never says she's a person, and never reads out her own instructions.
    if HUMAN_CLAIM.search(text):
        fixes.append("honesty")
        kept = [x for x in _sentences(text) if not HUMAN_CLAIM.search(x)
                and not re.fullmatch(r"(?:yes|yeah|yep|no|nope|of course|absolutely|sure)[,.!]*", x.strip(), re.I)]
        text = " ".join(["I'm Mila, an AI receptionist."] + kept)
    if ASKS_IF_AI.search(caller) and "honesty" not in fixes and not SAYS_AI.search(text):
        fixes.append("honesty")                      # asked straight out, she always says so
        kept = [x for x in _sentences(text) if not re.match(r"(?:no|nope|nah|yes|yep|yeah|of course|absolutely|sure|i am|i'm not)\b.{0,40}$", x.strip(), re.I)]
        text = " ".join(["I'm Mila, an AI receptionist."] + kept)
    manners_leak = False
    try:
        from shop_card import MANNERS
        said_words = re.findall(r"[a-z']+", text.lower())
        manners = " ".join(re.findall(r"[a-z']+", MANNERS.lower()))
        manners_leak = any(" ".join(said_words[i:i + 7]) in manners for i in range(max(0, len(said_words) - 6)))
    except Exception:
        pass
    if LEAK.search(text) or manners_leak:
        fixes.append("private")
        text = f"Sorry, I can't go into that. I can take a message for {owner}, or help with a booking."

    # 12. No risky do-it-yourself advice. She points to the emergency line instead.
    if DANGER.search(text):
        fixes.append("safety")
        kept = [x for x in _sentences(text) if not DANGER.search(x)]
        text = " ".join([f"I can't give advice on that. If you're in any danger, please hang up and call {emergency_line(country)}."] + kept)

    # 12b. No medical, legal or insurance advice, and never rude, whatever the caller says.
    if ADVICE.search(text):
        fixes.append("advice")
        kept = [x for x in _sentences(text) if not ADVICE.search(x)]
        text = " ".join(["Sorry, I can't advise on that."] + kept)
    if RUDE.search(text):
        fixes.append("manners")
        kept = [x for x in _sentences(text) if not RUDE.search(x)]
        text = " ".join(kept) or f"Sorry about that. I can take a message for {owner} if that helps."

    # 14. She only says she'll text, email, cancel, take a payment or put a call through if this shop's set-up can do it.
    abilities = a.get("abilities") or []
    abilities = {str(x).lower() for x in (abilities if isinstance(abilities, (list, tuple, set)) else [abilities])}
    cant = [k for k, rx in CANT_DO.items() if k not in abilities and rx.search(text)]
    if cant:
        fixes.append("cant_do")
        kept = [x for x in _sentences(text) if not any(CANT_DO[k].search(x) for k in cant)]
        text = " ".join(kept[:1] + [f"I can't do that from here, but I'll let {owner} know."])

    # 15. No sending callers to another business.
    shop_words = _letters(a.get("shop_name", ""))
    other_shops = [m.group(0) for m in REFERRAL.finditer(text)
                   if _letters(m.group(0)) not in shop_words and shop_words[:8] not in _letters(m.group(0))
                   and _letters(m.group(0)) not in _letters(heard_so_far + " " + caller)]
    if other_shops and a.get("shop_name"):
        fixes.append("referral")
        kept = [x for x in _sentences(text) if not any(o in x for o in other_shops)]
        text = " ".join(["Sorry, I can't recommend anyone else."] + kept)

    # 9c. Never read out an email or website that isn't the shop's or the caller's.
    known = (heard_so_far + " " + caller + " " + str(a)).lower()
    made_up_contact = [m.group(0) for rx in (EMAIL, URL) for m in rx.finditer(text) if m.group(0).lower().rstrip(".") not in known]
    if made_up_contact:
        fixes.append("made_up_detail")
        kept = [x for x in _sentences(text) if not any(c in x for c in made_up_contact)]
        text = " ".join(kept) or f"I don't have that in front of me. I can have {owner} call you back with it."

    # 9. Never read back a detail the caller hasn't given. An address she made up becomes a question.
    made_up = made_up_streets(text, heard_so_far + " " + caller)
    for m in PLAIN_STREET.finditer(_mask(spoken_numbers(text))):     # "99 fake street", written without capitals
        name = (m.group(2) + m.group(3)).strip()
        if name not in made_up and not _street_heard(name.title(), heard_so_far + " " + caller):
            made_up.append(m.group(0))
    if made_up:
        fixes.append("made_up_detail")
        kept = [x for x in _sentences(text) if not any(a_ in x for a_ in made_up) and not x.endswith("?")]
        text = " ".join(kept + ["What's the address for the job?"])

    # 9b. Never read back a phone number the caller hasn't given (or the shop's own).
    heard_all = spoken_numbers(heard_so_far + " " + caller)
    heard_digits = _digits(heard_all) + "|" + _digits(str(a.get("phone", "")))
    heard_phones = {_phone_digits(m.group(0)) for m in PHONE.finditer(heard_all)} | {_phone_digits(str(a.get("phone", "")))}
    call_has_phone = bool(PHONE.search(heard_all))
    fake = [] if (have_number and not call_has_phone) else \
        [m.group(0) for m in PHONE.finditer(text) if _digits(m.group(0)) not in heard_digits and _phone_digits(m.group(0)) not in heard_phones]
    if fake:
        fixes.append("made_up_detail")
        kept = [x for x in _sentences(text) if not any(f in x for f in fake) and not x.endswith("?")]
        # If the caller has just said their number, the read-back below gives the right one; otherwise ask.
        text = " ".join(kept + ([] if PHONE.search(caller) else ["What's the best number to reach you on?"]))

    # 2. Prices: only the ones on the card.
    if bad_prices(text, caller, a, heard_so_far + " " + last_reply):
        fixes.append("price")
        text = (f"I don't want to guess a price and get it wrong. I can have {owner} call you back with a proper one. "
                "Would that help?")

    # 11. No guarantees, refunds or licence claims unless the card says so.
    def _unbacked(x):
        return any(_squeeze(m.group(0)) not in card_blob for m in CLAIM.finditer(x)) and not HEDGED.search(x) and not x.rstrip().endswith("?")
    if any(_unbacked(x) for x in _sentences(text)):
        fixes.append("claim")
        kept = [x for x in _sentences(text) if not _unbacked(x) and not x.rstrip().endswith("?")]
        text = " ".join(kept[:1] + [f"I don't want to promise that and get it wrong. I can have {owner} call you back about it. Would that help?"])

    # 2b. Asked about cost: say the card's prices plainly instead of only "can't say".
    asked_price = re.search(r"\b(?:how much|price|cost|ballpark|quote|charge|fee|rough idea|some idea|any idea|roughly)\b", caller, re.I)
    card_prices = a.get("prices") or {}
    flat_no = re.search(r"\b(?:can't|cannot|won't|don't|not able|unable)\b[^.?!]*\b(?:price|quote|cost|figure)", text, re.I) \
        and not re.search(r"depends on the job", text, re.I)
    if asked_price and card_prices and flat_no and not MONEY.search(spoken_numbers(text)) and "price" not in fixes:
        listed = "; ".join(f"the {k} is {v}" for k, v in card_prices.items())
        if last_reply and "depends on the job" in last_reply:      # said it already: don't say it word for word again
            fixes.append("price_said")
            text = f"Honestly, {owner} needs to see the job before he can give a fair price. Want him to give you a call?"
            card_prices = {}
    if asked_price and card_prices and flat_no and not MONEY.search(spoken_numbers(text)) and "price" not in fixes:
        listed = "; ".join(f"the {k} is {v}" for k, v in card_prices.items())
        fixes.append("price_said")
        kept = [x for x in _sentences(text) if not x.endswith("?")][:1]
        text = " ".join(kept + [f"{listed[0].upper() + listed[1:]}, and the rest depends on the job. "
                                f"Would you like {owner} to call you with a proper price?"])

    # 2c. A service that isn't on the card either way: she doesn't know, so she offers a call back.
    asked_service = re.search(r"\bdo (?:you|ya|youse)(?: guys| blokes)? (?:do|offer|handle|fix|clean|repair|install|look at)\s+([^?.!]{3,40})", caller, re.I)
    if asked_service:
        stop = {"a", "an", "the", "any", "some", "your", "my", "of", "and", "or", "as", "well", "too", "also", "work", "jobs", "job", "do"}
        words = {w for w in re.findall(r"[a-z]+", asked_service.group(1).lower()) if w not in stop}
        known = " ".join(str(x).lower() for x in list(a.get("services") or []) + list(a.get("not_offered") or []))
        if words and not any(w in known or (w.endswith("s") and w[:-1] in known) for w in words):
            sure = re.search(r"\b(?:we (?:don't|do not|do|can|can't|cannot|offer|handle)|yes|yep|yeah|no,|sorry, (?:we|no))\b", text, re.I)
            if sure and not re.search(r"\bnot sure\b|\bcheck\b", text, re.I):
                fixes.append("unknown_service")
                text = f"I'm not sure about that one. I can have {owner} call you back to check. Would that help?"

    # 2d. The cost of a job itself: offer the call back the card promises, rather than quizzing the caller.
    job_cost = re.search(r"\b(?:whole job|job cost|cost of the job|all up|roughly|ballpark|how much (?:would|will) (?:it|the job))\b", caller, re.I)
    if job_cost and a.get("prices") is not None and not re.search(r"\b(?:call|ring)\b", text, re.I):
        sent = [x for x in _sentences(text) if not x.endswith("?")]
        fixes.append("price_call_back")
        text = " ".join(sent[:2] + [f"Would you like {owner} to call you with a proper price?"])

    # 2e. After a goodbye: a short, warm goodbye, no sales pitch.
    if re.search(r"\b(?:bye|goodbye|see ya|hooroo|catch ya)\b", caller, re.I) and len(text.split()) > 10:
        fixes.append("goodbye")
        text = f"No worries. Thanks for calling {a.get('shop_name', 'us')}."

    # 3a. Never say the shop doesn't work a day it does.
    days_open = {str(d).lower() for d in a.get("open_days", [])}
    closed_claim = re.compile(r"\b(?:don't|do not|aren't|are not|can't|cannot|never)\s+(?:do|open|work|come out|available|go out)?\s*"
                              r"(?:on\s+)?(?:a\s+)?" + DAY + r"s?\b", re.I)
    wrong = [x for x in _sentences(text) for m in closed_claim.finditer(x) if m.group(1).lower() in days_open]
    if wrong:
        fixes.append("closed_day")
        asked = SLOT.search(caller)
        why = f"Sorry, {asked.group(1).capitalize()} at {asked.group(2)} isn't free." if asked else "Sorry, that day's full."
        text = " ".join(why if x in wrong else x for x in dict.fromkeys(_sentences(text)))

    # 3. Days and times: only real free spots, only on working days.
    open_days = {str(d).lower() for d in a.get("open_days", [])}
    # A time with no day takes its day from the call: what the caller just said, then her last reply, then earlier.
    refused_now = refused_days(caller)
    caller_days = [m.group(1).lower() for m in re.finditer(DAY, caller, re.I) if m.group(1).lower() not in refused_now]
    refused = (refused_days(heard_so_far) | refused_now) - set(caller_days)     # "Thursday then" later takes it back
    recent_days = caller_days[-1:] if caller_days else [   # the day the caller last named wins outright
        m.group(1).lower() for src in (last_reply, heard_so_far) for m in reversed(list(re.finditer(DAY, src, re.I)))
        if m.group(1).lower() not in refused]
    free_now = None if diary is None else {(d.lower(), _norm_time(t)) for d, t in diary}

    def which_day(t):
        for d in recent_days:                      # prefer a recent day where that time is actually free
            if free_now is None or (d, t) in free_now:
                return d
        return recent_days[0] if recent_days else ""
    by_when = lambda x: BY_WHEN.sub(lambda m: " " if DOING.search(x) else m.group(0), x)      # "call you by 5pm" is a deadline, not a spot
    slot_text = " ".join(by_when(x) for x in _sentences(text))
    offered = [(d.lower() or which_day(_norm_time(t)), _norm_time(t)) for d, t in offered_slots(slot_text, "", today)]
    free = None if diary is None else {(d.lower(), _norm_time(t)) for d, t in diary}
    if free is not None and last_reply and BOOKED.search(last_reply):        # already booked: that spot has left the diary
        free |= {(d.lower(), _norm_time(t)) for d, t in offered_slots(last_reply, "", today) if d}
    def slot_ok(s):
        day, t = s
        if not day or day == "?":       # no day she or the caller named, or "tomorrow" without a date: can't check it
            return free is None and not open_days
        return (free is None or s in free) and (not open_days or day in open_days) and day not in refused
    bad_slot = any(not slot_ok(s) for s in offered)
    if offered and free is None:
        bad_slot = True          # she can't see the diary, so she can't offer a time
    # A day offered with no clock time ("Dave can come out on Sunday", "Wednesday morning") is checked too.
    part_ok = {"morning": lambda t: t.endswith("am"), "afternoon": lambda t: t.endswith("pm") and int(t.split(":")[0]) % 12 < 5,
               "arvo": lambda t: t.endswith("pm") and int(t.split(":")[0]) % 12 < 5,
               "evening": lambda t: t.endswith("pm") and 5 <= int(t.split(":")[0]) % 12, "night": lambda t: t.endswith("pm") and 5 <= int(t.split(":")[0]) % 12}
    agreed_days = {d.lower() for d, _ in offered_slots(last_reply, "", today) if d and d != "?"}
    for x in _sentences(spoken_numbers(text)):
        if bad_slot or HEDGED.search(x) or CALLBACK.search(x) or re.search(r"\b(?:hear (?:from|back)|(?:be|get) in touch|contact|reach out|expect a call)\b", x, re.I) \
                or re.search(r"\b(?:don't|doesn't|does not|do not|aren't|never|not on|not open|no good|instead of|rather than|closed|shut|did you say|you said|was that)\b", x, re.I):
            continue
        timed = {d.lower() for d, _ in offered_slots(by_when(x), "", today) if d}
        hours_talk = bool(HOURS_TALK.search(x) or re.search(r"\bwe work\b|\bworks? (?:on |from )?" + DAY, x, re.I)) and not re.search(r"\bwide open\b", x, re.I)
        commits = bool(DOING.search(x))
        offers = commits or hours_talk or bool(re.search(
            r"\b(?:how about|what about|i have|i've got|we have|we've got|free|available|suit|work for you|works|is fine|is good|is okay|is ok|"
            r"wide open|any ?time|all day|whenever|book|pencil|come (?:out|by|round|over)|see you|send|can do|could do|can fit|could fit|let's say)\b", x, re.I))
        if not offers:
            continue
        if not timed and re.search(r"\b(?:the )?\d{1,2}(?:st|nd|rd|th)\b|\b(?:january|february|march|april|june|july|august|september|october|november|december)\b", x, re.I):
            bad_slot = True                        # a calendar date can't be checked against the diary's days
            continue
        days = [d.lower() for d in re.findall(DAY, x, re.I) if d.lower() not in timed]
        if hours_talk:                             # "we're open Saturday": only wrong if the shop doesn't work that day
            bad_slot = bad_slot or any(open_days and d not in open_days for d in days)
            continue
        rel = RELATIVE.search(x)
        if rel and not days and today and str(today).lower() in WEEK and DOING.search(x) and re.search(r"\b(?:come|be there|be out|see you|fit you in|head over|pop)\b", x, re.I):
            days = [WEEK[(WEEK.index(str(today).lower()) + (1 if rel.group(1).lower() == "tomorrow" else 0)) % 7]]
        for day in days:
            if day in agreed_days:                 # she is repeating a day already checked on her last turn
                continue
            part = re.search(day + r"\s+(morning|afternoon|arvo|evening|night)", x, re.I)
            if (open_days and day not in open_days) or day in refused:
                bad_slot = True
            elif free is None:
                bad_slot = bad_slot or commits
            else:
                times = [t for d, t in free if d == day]
                if not times or (part and not any(part_ok[part.group(1).lower()](t) for t in times)):
                    bad_slot = True
    if bad_slot:
        fixes.append("time")
        if diary:
            d, t = next(((d, t) for d, t in diary if d.lower() not in refused), diary[0])
            asked = SLOT.search(caller)     # tell the caller why, if they asked for a spot that isn't free
            why = f"Sorry, {asked.group(1).capitalize()} at {asked.group(2)} isn't free. " if asked else ""
            text = f"{why}The next free spot is {d} at {t}. Would that suit?"
        else:
            text = (f"I can't see the diary just now, so I won't guess a time. What day suits you best, "
                    f"and I'll have {owner} confirm it?")

    # 3b. Opening hours: only the card's.
    card_hours = TIME_RANGE.search(a.get("open_hours", "") or "")
    if card_hours:
        def _nt(t, ref):
            if not re.search(r"[ap]\.?m", t, re.I):
                suffix = re.search(r"([ap])\.?m", ref, re.I)
                t += (suffix.group(1) + "m") if suffix else ""
            return _norm_time(t) if re.search(r"[ap]m", t.replace(".", ""), re.I) else t
        ct = re.findall(_T, card_hours.group(0))
        c_open, c_close = _nt(ct[0], ct[-1]), _nt(ct[-1], ct[-1])

        def wrong_hours(sentence):
            if not HOURS_TALK.search(sentence) and not re.search(r"\bwe work\b", sentence, re.I):
                return False
            for rng in TIME_RANGE.finditer(sentence):
                ts = re.findall(_T, rng.group(0))
                if not re.search(r"[ap]\.?m", rng.group(0), re.I):       # "7 to 4": compare the hours only
                    hour = lambda t: int(re.match(r"\d+", t).group(0)) % 12
                    if (hour(ts[0]), hour(ts[-1])) != (hour(ct[0]), hour(ct[-1])):
                        return True
                elif (_nt(ts[0], ts[-1]), _nt(ts[-1], ts[-1])) != (c_open, c_close):
                    return True
            for m in re.finditer(r"\b(open(?:s)?|close[sd]?|closes|shut|finish(?:es)?)\s+(?:at\s+)?(" + _T + r")(?![\w:])", sentence, re.I):
                want = c_open if m.group(1).lower().startswith("open") else c_close
                if _nt(m.group(2), m.group(2)) != want:
                    return True
            return False
        hours_parts = _sentences(text)
        if any(wrong_hours(x) for x in hours_parts):
            fixes.append("hours")
            asked = any(wrong_hours(x) and x.endswith("?") for x in hours_parts)
            kept = [x if not wrong_hours(x) else f"We work {a['open_hours']}." for x in hours_parts]
            if asked and diary:
                d, t = next(((d, t) for d, t in diary if d.lower() not in refused), diary[0])
                kept.append(f"The next free spot is {d} at {t}. Would that suit?")
            text = " ".join(dict.fromkeys(kept))

    # 3c. Booking: only after the caller says yes to a full read-back (day and time, name, number, address),
    # with a free spot in the diary. Otherwise she reads back, or asks for what is still missing.
    if BOOKED.search(text) and not (last_reply and BOOKED.search(last_reply)):
        call = spoken_numbers(heard_so_far + " " + caller)
        name = caller_name(heard_so_far + " " + caller) or caller_name(call)
        phones = [m.group(0) for m in PHONE.finditer(call)]
        addresses = [m.group(0) for m in ADDRESS_SAID.finditer(_mask(call))]
        lr = last_reply or ""
        lr_slots = [(d.lower(), _norm_time(t)) for d, t in offered_slots(lr, "", today)]
        slot = next((s_ for s_ in lr_slots + offered if free is not None and s_ in free and s_[0] not in refused), None)
        lr_phones = [_digits(m.group(0)) for m in PHONE.finditer(lr)]
        phone_ok = (phones and lr_phones and _phone_digits(lr_phones[-1]) == _phone_digits(phones[-1])) or (have_number and not phones and not lr_phones)
        confirmed = (YES.search(caller) and lr.rstrip().endswith("?") and slot is not None and slot in lr_slots and phone_ok
                     and ADDRESS_SAID.search(lr) and not made_up_streets(lr, heard_so_far))
        if a.get("bookings", "book") != "book":
            ask = f"I'll pass this to {owner} so he can lock in a time with you."
        elif confirmed:
            ask = None
        elif diary is None:
            ask = f"I can't see the diary just now, so I won't book it in yet. I'll have {owner} call you to lock in a time."
        elif not name:
            ask = "Can I grab your name?"
        elif not phones and not have_number:
            ask = "What's the best number to reach you on?"
        elif not addresses:
            ask = "What's the address for the job?"
        elif slot is None:
            d, t = next(((d, t) for d, t in diary if d.lower() not in refused), diary[0])
            ask = f"The next free spot is {d} at {t}. Would that suit?"
        else:
            day = next(d for d, _ in diary if d.lower() == slot[0])
            tm = next(t for d, t in diary if d.lower() == slot[0] and _norm_time(t) == slot[1])
            ph = _phone_digits(phones[-1]) if phones else ""
            ph = f"{ph[:4]} {ph[4:7]} {ph[7:]}" if len(ph) == 10 and ph.startswith("04") else (phones[-1] if phones else "")
            number = f" on {ph}" if ph else ""
            ask = f"Just to check: {day} at {tm}, {name}{number}, at {addresses[-1].strip(' ,').title()}. Is that right?"
        if ask:
            fixes.append("booking")
            kept = [x for x in _sentences(text) if not BOOKED.search(x) and not x.endswith("?") and not offered_slots(x)
                    and not ((VAGUE_SOON.search(x) or SOON.search(x)) and DOING.search(x))]
            text = " ".join(kept[:1] + [ask])

    # 6. If she asks "what time suits?" while free spots are in front of her, offer one instead.
    if diary and not offered and ASK_WHEN.search(text):
        fixes.append("offer_spot")
        said_days = [d for d, _ in diary if d.lower() in caller.lower()]
        open_spots = [s for s in diary if s[0].lower() not in refused] or list(diary)    # never offer a day they said no to
        picks = [s for s in open_spots if s[0] in said_days and s[0].lower() not in refused][:1] or list(open_spots[:2])
        offer = (f"I have {picks[0][0]} at {picks[0][1]}. Would that suit?" if len(picks) == 1 else
                 f"The next free spots are {picks[0][0]} at {picks[0][1]} or {picks[1][0]} at {picks[1][1]}. Would either suit?")
        kept = [s for s in _sentences(text) if not s.endswith("?")][:1]
        text = " ".join(kept + [offer])

    # 5d. She can't know where the owner is or how soon he'll turn up: "on his way", "five minutes away", "in a tick".
    if any(ETA.search(x) and not HEDGED.search(x) and not x.rstrip().endswith("?") for x in _sentences(text)):
        fixes.append("promise")
        line = f"I can't say exactly when, but I'll let {owner} know."
        text = " ".join(dict.fromkeys(line if (ETA.search(x) and not HEDGED.search(x) and not x.rstrip().endswith("?")) else x for x in _sentences(text)))

    # 5a. Deadlines: only on an urgent call, and only the one the card's urgent rule promises.
    promised = {m.group(0).lower() for m in DEADLINE.finditer(a.get("emergencies", ""))} if urgent else set()
    if any(m.group(0).lower() not in promised for m in DEADLINE.finditer(text)):
        fixes.append("deadline")
        text = DEADLINE.sub(lambda m: m.group(0) if m.group(0).lower() in promised else "as soon as possible", text)

    # 5b. No "today" or "this arvo" for when the owner will call or come: she can't know that.
    def soften(sentence: str) -> str:
        if DOING.search(sentence) and not HEDGED.search(sentence):
            if BY_WHEN.search(sentence) and not sentence.rstrip().endswith("?"):
                sentence = BY_WHEN.sub("as soon as possible", sentence)
            elif SOON.search(sentence) and not SLOT.search(sentence) and not CLOCK.search(sentence):
                # Only the "when" that belongs to the promise: "Dave's on a job right now, but I can have him call you" is fine.
                at = DOING.search(sentence).start()
                head, tail = sentence[:at], sentence[at:]
                if not re.search(r",|\bbut\b|\band\b|\bso\b", head):
                    head = SOON.sub("as soon as possible", head)
                sentence = head + SOON.sub("as soon as possible", tail)
            sentence = re.sub(r"(as soon as possible)(?:,? (?:and |or )?as soon as possible)+", r"\1", sentence)
            return re.sub(r"\s{2,}", " ", sentence)
        return sentence
    softened = " ".join(soften(x) for x in _sentences(text))
    if not urgent and softened != " ".join(_sentences(text)):
        fixes.append("promise")
        text = softened

    # 5c. "He'll be with you shortly" is a promise too, and there is no office to be back in.
    if not urgent:
        kept = _sentences(text)
        if SLOT.search(text):     # a visit is booked for a set time, so "shortly" contradicts it
            kept = [x for x in kept if SLOT.search(x) or not (VAGUE_SOON.search(x) and DOING.search(x) and not HEDGED.search(x))]
        fixed = OFFICE.sub("as soon as possible", " ".join(kept))
        if fixed != " ".join(_sentences(text)):
            if "promise" not in fixes:
                fixes.append("promise")
            text = fixed

    # 10. She goes along with slang, she doesn't start it.
    if MATE.search(text) and "mate" not in everything_heard:
        fixes.append("slang")
        text = MATE.sub("", text)

    # "Would you like to book, or is there something else I can help with?": keep only the real question.
    tail_off = re.sub(r",? or (?:is there )?(?:anything|something) else (?:i can|we can|you need|you'd like)[^?]*\?", "?", text, flags=re.I)
    if tail_off != text:
        fixes.append("sign_off")
        text = tail_off

    # 7b. No chatbot sign-offs, and not too long for a phone call.
    parts = _sentences(text)
    real = [x for x in parts if not FILLER.match(x) and not (ANYTHING_ELSE.match(x) and not (have_number or PHONE.search(caller)))]
    if real and len(real) < len(parts):
        fixes.append("sign_off")
        parts = real
        text = " ".join(parts)
    if len(parts) > MAX_SENTENCES:
        fixes.append("too_long")
        # Drop padding first ("That's a free spot in the diary."), then empty acknowledgements, later ones before the opener.
        parts = [x for x in parts if not FLUFF.match(x)] or parts
        for i in sorted((i for i, x in enumerate(parts) if ACK.match(x) and len(x.split()) <= 5), key=lambda i: (i == 0, -i)):
            if len(parts) - 1 >= MAX_SENTENCES or len(parts) > MAX_SENTENCES:
                parts = parts[:i] + parts[i + 1:]
            if len(parts) <= MAX_SENTENCES:
                break
        text = " ".join(parts)
    if len(parts) > MAX_SENTENCES:
        # Keep any sentence carrying a number, address or time (a read-back), and her last question.
        chosen = {i for i, x in enumerate(parts)
                  if re.search(r"\d|\b(?:unit|flat|apartment)\b", x, re.I) or STREET.search(x) or offered_slots(x)}
        last_q = next((i for i in range(len(parts) - 1, -1, -1) if parts[i].endswith("?")), None)
        chosen.add(last_q if last_q is not None else MAX_SENTENCES - 1)
        for i in range(len(parts)):
            if len(chosen) >= MAX_SENTENCES:
                break
            chosen.add(i)
        text = " ".join(parts[i] for i in sorted(chosen))

    # 9d. Never call the caller by a name they didn't give.
    known_name = caller_name(heard_so_far + " " + caller)
    def _right_name(m):
        said_name = m.group(2)
        if said_name.lower() in everything_heard or said_name in (owner, "Mila") or said_name.lower() in WEEK \
                or said_name in NOT_NAMES or said_name.lower() in NOT_NAME_WORDS | {"thanks", "there", "then", "you", "and", "but", "now", "sure", "well", "all", "mate"}:
            return m.group(0)
        return f"{m.group(1)}, {known_name.split()[0]}" if known_name else m.group(1)
    renamed = GREET_NAME.sub(_right_name, text) if everything_heard.strip() else text    # nothing heard yet: nothing to check against
    if renamed != text:
        fixes.append("name")
        text = renamed

    # 1. Read back a number the caller just gave, first, as a statement, so her own question still comes last.
    said = [m.group(0) for m in PHONE.finditer(caller)]
    if said:
        have_number = True
        text_phones = {_phone_digits(m.group(0)) for m in PHONE.finditer(text)}
        if not any(_digits(n) in _digits(text) or _phone_digits(n) in text_phones for n in said):
            fixes.append("read_back")
            name = caller_name(caller)
            # The read-back already thanks them by name, so drop the brain's own "Sure thing, Tom." / "I've noted..." lines.
            rest = [x for x in _sentences(text) if not ((ACK.match(x) and len(x.split()) <= 4) or NOTED.match(x))]
            text = (f"So that's {name} on {said[-1]}. " if name else f"So that's {said[-1]}. ") + " ".join(rest)
            text = text.strip()

    # 1b. Read back an address the caller just gave, with every number in it.
    addr_m = list(ADDRESS_SAID.finditer(_mask(caller)))
    if addr_m:
        addr = caller[addr_m[-1].start():addr_m[-1].end()].strip(" ,")
        nums = re.findall(r"\d+", addr)
        if nums and not all(re.search(r"(?<!\d)" + n + r"(?!\d)", spoken_numbers(text)) for n in nums):
            fixes.append("read_back")
            nice = re.sub(r"\b([a-z])", lambda m: m.group(1).upper(), addr) if addr.islower() else addr
            rest = [x for x in _sentences(text) if not ((ACK.match(x) and len(x.split()) <= 4) or NOTED.match(x))]
            text = (f"So that's {nice}. " + " ".join(rest)).strip()

    # 5d. A visit is never "as soon as possible": offer a real spot instead. And say "as soon as" once.
    visit = re.compile(r"\b(?:come|come out|be there|be out|pop (?:over|round)|head over|get out|send someone|arrange someone)\b", re.I)
    if not urgent and diary and "promise" in fixes:
        sent = _sentences(text)
        if any("as soon as possible" in x and visit.search(x) for x in sent):
            d, t = next(((d, t) for d, t in diary if d.lower() not in refused), diary[0])
            kept = [x for x in sent if not ("as soon as possible" in x and visit.search(x)) and not x.endswith("?")]
            text = " ".join(kept + [f"The next free spot is {d} at {t}. Would that suit?"])
    sent = _sentences(text)
    if sum("as soon as" in x for x in sent) > 1:
        last = max(i for i, x in enumerate(sent) if "as soon as" in x)
        text = " ".join(re.sub(r",? as soon as possible", "", x) if i < last else x for i, x in enumerate(sent))

    # 12. One thing at a time: name, then number, then address. A call back never needs an address.
    call_so_far = heard_so_far + " " + caller
    wants_call_back = bool(re.search(r"\b(?:call|ring|phone) me\b|\bcall(?:s)? (?:me )?back\b|\bget (?:him|her|them|\w+) to (?:call|ring)\b",
                                     call_so_far, re.I)) or a.get("bookings", "book") != "book"
    have_name = bool(caller_name(call_so_far))
    have_phone = have_number or bool(PHONE.search(spoken_numbers(call_so_far)))
    have_address = bool(ADDRESS_SAID.search(_mask(spoken_numbers(call_so_far))))
    parts_q = _sentences(text)
    for i, q in enumerate(parts_q):
        if not q.endswith("?"):
            continue
        asks = [k for k, rx in (("name", r"\bname\b"), ("number", r"\b(?:phone )?number\b|\bphone\b|\bmobile\b"),
                                 ("address", r"\baddress\b|\bwhere (?:are you|is the job)\b")) if re.search(rx, q, re.I)]
        if wants_call_back and "address" in asks:
            asks.remove("address")
            if not asks:
                asks = ["none"]
        urgent_first = urgent and asks == ["name"] and not (have_address and have_phone)
        if len(asks) > 1 or asks == ["none"] or urgent_first:
            order = (("address", have_address), ("number", have_phone), ("name", True)) if urgent else \
                    (("name", have_name), ("number", have_phone), ("address", have_address or wants_call_back))
            missing = [k for k, have in order if not have]
            nxt = missing[0] if missing else None
            fixes.append("one_ask")
            parts_q[i] = {"name": "Can I grab your name?", "number": "What's the best number to reach you on?",
                          "address": "What's the address for the job?", None: ""}[nxt]
    if "one_ask" in fixes:
        text = " ".join(x for x in parts_q if x) or "Thanks, I've got that."

    # 13. Urgent: once address and number are in, say what the card promises ("Dave will ring within fifteen minutes").
    promise_m = DEADLINE.search(a.get("emergencies", "") or "")
    if urgent and promise_m and have_address and have_phone and not DEADLINE.search(text) \
            and not DEADLINE.search(last_reply or ""):
        fixes.append("urgent_promise")
        kept = [x for x in _sentences(text) if not x.endswith("?")]
        text = " ".join(kept + [f"{owner} will ring you {promise_m.group(0)}."])

    # 4. No call back promised without a number.
    # (Skipped when she is already asking something: one question at a time.)
    owner_calls = re.search(r"\b(?:call|ring|phone|get back to) you\b|\b(?:he|she|they|we|" + re.escape(owner) + r")(?:'ll| will| can)?\s+(?:give you a )?(?:call|ring)", text, re.I)
    goodbye = re.search(r"\b(?:bye|goodbye|see ya|hooroo|catch ya)\b", caller, re.I)
    if CALLBACK.search(text) and owner_calls and not goodbye and not have_number and not text.rstrip().endswith("?") \
            and not re.search(r"number", text, re.I):
        fixes.append("need_number")
        text = text.rstrip() + f" What's the best number for {owner} to call?"

    if not re.search(r"[A-Za-z0-9]", text):          # nothing left after the fixes: still never silence
        fixes.append("empty")
        text = "Sorry, could you say that again?"
    return Guarded(text, fixes)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from shop_card import ShopCard
    card = ShopCard.load(Path(__file__).resolve().parent.parent / "shop" / "examples" / "birch-and-co.json")
    diary = [("Tuesday", "9:30am"), ("Thursday", "2:00pm")]
    for caller, reply in [
        ("Can you get Dave to call me back? It's Bec, 0412 345 678.", "I'll pass your call to Dave."),
        ("There's water pouring through my ceiling!", "That's an emergency. I'll get Dave to call you back now."),
        ("How much for a leaking tap?", "It's usually about $150 for a tap."),
        ("Can someone come this week?", "Sure, I can do Wednesday at 10am."),
        ("What's the call-out fee?", "The call-out fee is $90."),
    ]:
        out = guard(reply, caller, card, diary)
        print(f"caller: {caller}\n brain: {reply}\n spoken: {out.text}   {out.fixes or ''}\n")
