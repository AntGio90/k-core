from cat.mad_hatter.decorators import hook
import re

@hook(priority=1)
def before_cat_sends_message(final_output, cat):
    # You can edit the final_output the Cat is about to send back to the user
    # Remove everything between <think> and </think> tags (including the tags)
    
    settings = cat.mad_hatter.get_plugin().load_settings()
    
    if not settings.get("show_reasoning"):
        print("********** before_cat_sends_message ************")
        final_output.content = re.sub(r"<think[\s\S]*?</think>", "", final_output.content, flags=re.IGNORECASE).strip()

    return final_output