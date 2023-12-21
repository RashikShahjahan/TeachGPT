# Extract the stories from english_stories.json and write them to a file
# in the format expected by the story generator.
import json


def write_stories_to_file():
    stories = json.load(open('english_stories.json'))
    for story in stories:
        story = story['story']
        with open('english_stories.txt', 'a', encoding='utf-8') as file:
            file.write(story + '\n')

write_stories_to_file()