CONSUMERS = []


def register(consumer_cls):
    """
    Register a consumer class so it can be started automatically.
    """
    try:
        if consumer_cls not in CONSUMERS:
            CONSUMERS.append(consumer_cls)
    except Exception as e:
        raise e
    finally:
        return CONSUMERS

