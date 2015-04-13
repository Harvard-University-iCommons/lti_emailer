from django.apps import AppConfig


class MailingListConfig(AppConfig):
    name = 'mailing_list'
    verbose_name = 'Mailing List'

    def ready(self):
        # Import signals module to connect receivers defined there
        import signals
