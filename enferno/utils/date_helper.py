import arrow 

class DateHelper:
    @staticmethod
    def serialize_datetime(dt):
        return arrow.get(dt).format('YYYY-MM-DDTHH:mm') if dt else None

    @staticmethod
    def file_date_parse(dt):
        try:
         d = arrow.get(dt, 'YYYY:MM:DD HH:mm:ss').format('YYYY-MM-DDTHH:mm') if dt else None
         return d
        except Exception as e:
            print (e)
            return None

