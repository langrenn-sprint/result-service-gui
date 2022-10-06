"""Module for image services."""
import logging

from google.cloud import vision  # type: ignore
import requests

from .events_adapter import EventsAdapter


class AiImageService:
    """Class representing image services."""

    def analyze_photo_with_google_detailed(self, image_uri: str) -> dict:
        """Send infile to Google Vision API, return dict with all labels, objects and texts."""
        logging.debug("Enter Google vision API")
        _tags = {}

        # Instantiates a client
        client = vision.ImageAnnotatorClient()
        image = vision.Image()
        image.source.image_uri = image_uri

        # Performs label detection on the image file
        response = client.label_detection(image=image)
        labels = response.label_annotations
        for label in labels:
            logging.debug(f"Found label: {label.description}")
            _tags["Label"] = label.description

        # Performs object detection on the image file
        objects = client.object_localization(image=image).localized_object_annotations
        for object_ in objects:
            logging.debug(
                "Found object: {} (confidence: {})".format(object_.name, object_.score)
            )
            _tags["Object"] = object_.name

        # Performs text detection on the image file
        response = client.document_text_detection(image=image)
        for page in response.full_text_annotation.pages:
            for block in page.blocks:
                logging.debug("\nBlock confidence: {}\n".format(block.confidence))

                for paragraph in block.paragraphs:
                    logging.debug(
                        "Paragraph confidence: {}".format(paragraph.confidence)
                    )

                    for word in paragraph.words:
                        word_text = "".join([symbol.text for symbol in word.symbols])
                        logging.debug(
                            "Word text: {} (confidence: {})".format(
                                word_text, word.confidence
                            )
                        )

                        for symbol in word.symbols:
                            logging.debug(
                                "\tSymbol: {} (confidence: {})".format(
                                    symbol.text, symbol.confidence
                                )
                            )

        if response.error.message:
            raise Exception(
                "{}\nFor more info on error messages, check: "
                "https://cloud.google.com/apis/design/errors".format(
                    response.error.message
                )
            )

        return _tags

    def analyze_photo_with_google_for_langrenn(self, image_uri: str) -> dict:
        """Send infile to Vision API, return dict with langrenn info."""
        logging.info(f"Enter vision, image {image_uri}")
        _tags = {}
        count_persons = 0

        try:
            # Instantiates a client
            client = vision.ImageAnnotatorClient()
            # Loads the image into memory
            content = requests.get(image_uri).content
            image = vision.Image(content=content)
        except Exception as e:
            logging.error(f"Error connecting to VisionAI service: {e}")
            raise Exception(f"Kunne ikke koble til GoogleVisionAI. {e}") from e

        # Performs object detection on the image file
        objects = client.object_localization(image=image).localized_object_annotations
        for object_ in objects:
            logging.debug(
                "Found object: {} (confidence: {})".format(object_.name, object_.score)
            )
            if (
                float(EventsAdapter().get_global_setting("CONFIDENCE_LIMIT"))
                < object_.score
            ):
                if object_.name == "Person":
                    count_persons = count_persons + 1
        _tags["Persons"] = count_persons

        # Performs text detection on the image file
        _numbers = []
        _texts = []
        response = client.document_text_detection(image=image)
        for page in response.full_text_annotation.pages:
            for block in page.blocks:
                for paragraph in block.paragraphs:
                    for word in paragraph.words:
                        if (
                            float(
                                EventsAdapter().get_global_setting("CONFIDENCE_LIMIT")
                            )
                            < word.confidence
                        ):
                            word_text = "".join(
                                [symbol.text for symbol in word.symbols]
                            )
                            logging.debug(
                                "Word text: {} (confidence: {})".format(
                                    word_text, word.confidence
                                )
                            )
                            if word_text.isnumeric():
                                _numbers.append(int(word_text))
                            else:
                                _texts.append(word_text)
        _tags["ai_numbers"] = _numbers  # type: ignore
        _tags["ai_text"] = _texts  # type: ignore

        if response.error.message:
            raise Exception(
                "{}\nFor more info on error messages, check: "
                "https://cloud.google.com/apis/design/errors".format(
                    response.error.message
                )
            )

        return _tags
