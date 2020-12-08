import arrow 

class DateHelper:
    @staticmethod
    def serialize_datetime(dt):
        return arrow.get(dt).format('YYYY-MM-DDTHH:mm') if dt else None

