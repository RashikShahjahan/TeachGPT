import openai
import random
import pika
import configparser
import logging

config = configparser.ConfigParser()
config.read('config.ini')

AMPQ_URL = config['RabbitMQ']['AMQP_URL']

def get_response(instructions):
    messages = [
        { "role": "system", "content": instructions },
    ]

    completion = openai.chat.completions.create(
        model="gpt-4",
        messages=messages,
    )

    return completion.choices[0].message.content

def read_words_from_file(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        return [line.strip() for line in file.readlines() if line.strip()]

def generate_story_prompt():
    # Read the sets from their respective files
    verbs = read_words_from_file('verbs.txt')
    nouns = read_words_from_file('nouns.txt')
    adjectives = read_words_from_file('adjectives.txt')
    features = ["dialogue", "plot twist", "bad ending" ,"good ending" "moral value"]

    # Randomly choose one verb, noun, and adjective
    chosen_verb = random.choice(verbs)
    chosen_noun = random.choice(nouns)
    chosen_adjective = random.choice(adjectives)

    # Randomly choose a number of features (between 1 and the length of the features list)
    chosen_features = random.sample(features, random.randint(1, len(features)))

    # Create the prompt
    prompt = f"Write a short story in Bengali (3-5 paragraphs) which only uses very simple words that a 3-4 year old child would likely understand. The story should use the verb “{chosen_verb}”, the noun “{chosen_noun}” and the adjective “{chosen_adjective}”. The story should have the following features: {', '.join(chosen_features)}. Remember to only use simple Bengali words!"
    return prompt

def write_to_rabbitmq(story, amqp_url):
    try:
        # Parse the AMQP URL with credentials
        parameters = pika.URLParameters(amqp_url)

        # Establish a connection
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        # Declare the queue
        channel.queue_declare(queue='story_queue', durable=True)

        # Ensure the story is a byte string
        if isinstance(story, str):
            story = story.encode()

        # Publish the message
        channel.basic_publish(exchange='', routing_key='story_queue', body=story)
        logging.info("Message sent to RabbitMQ")
    except pika.exceptions.AMQPConnectionError as e:
        logging.error(f"Failed to connect to RabbitMQ: {e}")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        # Close the connection if it's open
        if 'connection' in locals() and connection.is_open:
            connection.close()
            logging.info("RabbitMQ connection closed")

while True:
    story_prompt = generate_story_prompt()
    print(story_prompt)
    story = get_response(story_prompt)
    write_to_rabbitmq(story, AMPQ_URL)