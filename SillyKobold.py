import json
import sys
import re
from datetime import datetime

def parse_koboldai_actions(actions, kobold_user_name):
    parsed_lines = []
    current_speaker = None
    current_message = []

    for action in actions:
        lines = action.strip().split('\n')
        for line in lines:
            if line.startswith(f"{kobold_user_name}:"):
                if current_speaker is not None and current_message:
                    parsed_lines.append((current_speaker, " ".join(current_message)))
                current_speaker = kobold_user_name
                current_message = [line.split(f"{kobold_user_name}: ", 1)[1].strip()]
            else:
                match = re.match(r"(\w+):\s*(.*)", line.strip())
                if match:
                    if current_speaker is not None and current_message:
                        parsed_lines.append((current_speaker, " ".join(current_message)))
                    current_speaker = match.group(1)
                    current_message = [match.group(2).strip()]
                else:
                    current_message.append(line.strip())

    if current_speaker is not None and current_message:
        parsed_lines.append((current_speaker, " ".join(current_message)))

    return parsed_lines

def convert_chat_line(speaker, message, player_name, date_str, api_name, model_name):
    is_user = speaker == player_name
    
    chat_entry = {
        "name": speaker,
        "is_user": is_user,
        "is_system": False,
        "send_date": date_str,
        "mes": message,
        "extra": {
            "isSmallSys": False
        },
        "force_avatar": "" if is_user else None
    }
    
    # Only add generation metadata for AI-generated messages
    if not is_user:
        chat_entry.update({
            "extra": {
                "api": api_name,
                "model": model_name
            },
            "gen_started": f"{date_str}T00:01:00.000Z",
            "gen_finished": f"{date_str}T00:01:00.000Z",
            "swipe_id": 0,
            "swipes": [message],
            "swipe_info": [
                {
                    "send_date": date_str,
                    "gen_started": f"{date_str}T00:01:00.000Z",
                    "gen_finished": f"{date_str}T00:01:00.000Z",
                    "extra": {
                        "api": api_name,
                        "model": model_name
                    }
                }
            ]
        })

    return chat_entry

def convert_logs(sillytavern_file, koboldai_file, sillytavern_user, koboldai_user, output_file):
    with open(sillytavern_file, 'r') as st_file:
        sillytavern_data = [json.loads(line) for line in st_file.readlines()]

    with open(koboldai_file, 'r') as ka_file:
        koboldai_data = json.load(ka_file)

    # Extract relevant information
    koboldai_actions = koboldai_data.get('actions', [])
    date_str = "January 1, 2020 12:01am"
    api_name = "koboldcpp"
    model_name = "koboldcpp/unknown"

    # Parse KoboldAI actions into speaker-message pairs
    parsed_chats = parse_koboldai_actions(koboldai_actions, koboldai_user)

    # Convert each parsed chat into a SillyTavern formatted chat entry
    converted_chats = []
    for speaker, message in parsed_chats:
        converted_chats.append(
            convert_chat_line(speaker, message, sillytavern_user, date_str, api_name, model_name)
        )

    # Copy over the original metadata from the first SillyTavern entry
    if sillytavern_data:
        metadata = sillytavern_data[0].get("chat_metadata", {})
        for chat in converted_chats:
            chat["chat_metadata"] = metadata

    # Write the converted log to the output file
    with open(output_file, 'w') as out_file:
        for chat in converted_chats:
            json.dump(chat, out_file)
            out_file.write('\n')

if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Usage: python SillyKobold.py <SillyTavern_log> <KoboldAI_log> <SillyTavern_user> <KoboldAI_user> <Output_file>")
        sys.exit(1)

    sillytavern_file = sys.argv[1]
    koboldai_file = sys.argv[2]
    sillytavern_user = sys.argv[3]
    koboldai_user = sys.argv[4]
    output_file = sys.argv[5]

    convert_logs(sillytavern_file, koboldai_file, sillytavern_user, koboldai_user, output_file)
