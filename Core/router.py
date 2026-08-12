def route_input(input_text):
    if "remember" in input_text:
        return "memory"
    elif "feel" in input_text:
        return "emotion"
    return "conversation"