from object_store.s3_object_store import S3ObjectStore


class ObjectStoreFactory:

    @staticmethod
    def create(config):

        provider = config["object_store"]["provider"]

        if provider == "s3":
            return S3ObjectStore(config)

        raise ValueError(
            f"Unsupported object store: {provider}"
        )