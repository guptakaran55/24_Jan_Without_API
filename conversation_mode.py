# conversation_mode.py
# Ask the user how much time they have, and adjust settings accordingly

def select_conversation_mode():
    """
    Ask the user how much time they want to spend.
    Returns a dict of settings that other modules can use.
    """
    
    print("\n" + "=" * 80)
    print("⏱️  HOW MUCH TIME DO YOU HAVE?")
    print("=" * 80)
    print()
    print("  1. ⚡ Quick (5-10 min)    — Fast data collection, minimal chat")
    print("  2. ☕ Normal (10-20 min)   — Balanced conversation with some chat")
    print("  3. 🛋️  Relaxed (20-40 min)  — Detailed discussion, fun tangents welcome")
    print("  4. 🎉 All the time! (40+ min) — Deep conversation, stories, opinions, everything!")
    print()
    
    while True:
        try:
            choice = input("Select mode (1-4): ").strip()
            idx = int(choice)
            
            if 1 <= idx <= 4:
                mode = MODES[idx]
                print(f"\n✓ Mode: {mode['label']}")
                print(f"  {mode['description']}\n")
                return mode
            else:
                print("❌ Please enter 1, 2, 3, or 4")
        except ValueError:
            print("❌ Please enter a valid number")
        except KeyboardInterrupt:
            print("\n\n👋 Exiting...\n")
            exit(0)


# ─────────────────────────────────────────────────
# Mode definitions
# ─────────────────────────────────────────────────

MODES = {
    1: {
        'key': 'quick',
        'label': '⚡ Quick Mode',
        'description': 'Straight to the point. Minimal small talk.',
        
        # LLM output token limits
        'max_output_tokens': 3072,
        
        # How many conversation history messages to send to LLM
        # (minimum 15 to avoid forgetting earlier answers)
        'history_limit': 15,
        
        # Prompt style additions
        'prompt_style': (
            "CONVERSATION MODE: QUICK\n"
            "- Be brief and efficient. Short sentences.\n"
            "- Skip small talk — go straight to appliance questions.\n"
            "- Extract data as fast as possible.\n"
            "- Don't discuss hobbies, opinions, or tangents.\n"
            "- Aim to collect all appliances in under 10 messages.\n"
            "- When user mentions an appliance with enough info, OUTPUT JSON IMMEDIATELY.\n"
            "- Do NOT keep asking clarifying questions if you can make reasonable estimates.\n"
        ),
    },
    
    2: {
        'key': 'normal',
        'label': '☕ Normal Mode',
        'description': 'Friendly and efficient. A bit of chat, but stays on track.',
        
        'max_output_tokens': 4096,
        'history_limit': 20,
        
        'prompt_style': (
            "CONVERSATION MODE: NORMAL\n"
            "- Be friendly and warm, but stay focused.\n"
            "- Brief acknowledgments before moving to next appliance.\n"
            "- A little small talk is okay, but don't go on tangents.\n"
            "- Keep responses to 2-4 sentences plus any JSON blocks.\n"
        ),
    },
    
    3: {
        'key': 'relaxed',
        'label': '🛋️ Relaxed Mode',
        'description': 'Take your time. Chat about life, share fun facts.',
        
        'max_output_tokens': 6144,
        'history_limit': 30,
        
        'prompt_style': (
            "CONVERSATION MODE: RELAXED\n"
            "- Take your time. Be conversational and engaging.\n"
            "- Share interesting energy facts, fun trivia, or tips.\n"
            "- Discuss the user's interests if they bring them up.\n"
            "- Ask about their lifestyle, hobbies, and daily routines naturally.\n"
            "- Feel free to make the conversation enjoyable.\n"
            "- Responses can be 3-6 sentences plus JSON blocks.\n"
        ),
    },
    
    4: {
        'key': 'deep',
        'label': '🎉 Deep Conversation Mode',
        'description': 'Full experience! Stories, opinions, energy tips, life chat.',
        
        'max_output_tokens': 8192,
        'history_limit': 40,
        
        'prompt_style': (
            "CONVERSATION MODE: DEEP CONVERSATION\n"
            "- This user has plenty of time and wants a rich experience.\n"
            "- Be like a knowledgeable friend having a long chat over tea.\n"
            "- Share detailed energy-saving tips and explain WHY.\n"
            "- Discuss topics they care about: politics, movies, science, sports, etc.\n"
            "- Tell relevant stories, analogies, and fun facts.\n"
            "- For children: talk about cartoons, science experiments, cool facts.\n"
            "- For adults: discuss current events, compare energy habits globally.\n"
            "- Make this the most interesting survey they've ever done!\n"
            "- Responses can be as long as needed to be genuinely engaging.\n"
        ),
    },
}


def get_mode_by_key(key):
    """Get a mode by its string key (useful for config files)"""
    for mode in MODES.values():
        if mode['key'] == key:
            return mode
    return MODES[2]  # Default to normal