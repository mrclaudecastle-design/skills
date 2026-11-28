"""A second set of 12 scripted calls, kept apart from the main 12 in live_call_test.py.

The main set is what every round is scored on, so fixes slowly get tuned to it.
This set checks that a fix also holds on calls the safety net was not built around.
Play it with:  rehearse_gguf.py --set more   (or live_call_test.py --set more on the Mac)
"""

MORE_CALLS = {
    "unit address": ["Hi, the toilet won't stop running. Can someone come Thursday?", "Yep, that's fine.",
                     "It's Priya Shah, unit 3, 47 Pittwater Road.", "Oh four one nine, two two two, three three three."],
    "street with no type": ["Need someone for a blocked sink, Friday if you can.", "Friday's good.",
                            "Mark, 22 Ocean, Bondi.", "0400 123 456."],
    "number corrected": ["Can Dave give me a ring about a quote for a new hot water system?", "It's Jess, 0422 555 018.",
                         "Sorry, I mean 0422 555 081."],
    "is this a person": ["Am I talking to a real person?", "Alright. Can you book me in Tuesday morning?", "Yes, 9:30 is fine."],
    "opening hours": ["What hours do you work?", "Do you do Saturdays?"],
    "wants to cancel": ["I need to cancel my booking for Thursday.", "It's Shane, 0412 345 678."],
    "smell of gas": ["I can smell gas in the kitchen, can you send someone?"],
    "all in one breath": ["Hi, I'm Alan Chu, 0433 111 222, 5 Wattle Street, my kitchen tap's dripping, can someone come Tuesday at 9:30?",
                          "Yes, that's all right."],
    "rude caller": ["This is ridiculous, nobody ever answers, are you useless?", "Fine. Just get Dave to call me. It's Rob, 0499 876 543."],
    "after hours visit": ["Can someone come at 6pm tonight?", "What's the earliest then?"],
    "regular customer": ["It's Helen again, Dave fixed my hot water last month and it's playing up.", "Can he call me? 0411 222 333."],
    "vague caller": ["Um, hi, yeah, I've got a sort of a problem with, like, water?", "It's coming up out of the drain in the yard.",
                     "Whenever's fine."],
}
