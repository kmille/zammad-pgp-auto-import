
class PGPImportError(Exception):
    pass


class PGPError(PGPImportError):
    pass


class NotFoundOnKeyserverError(PGPImportError):
    pass


class ZammadError(PGPImportError):
    pass


class ZammadPGPKeyAlreadyImportedError(PGPImportError):
    pass
