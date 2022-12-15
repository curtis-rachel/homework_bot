class APIRequestError(Exception):
    """Error endpoint."""

    def __init__(self, text):
        self.txt = text
