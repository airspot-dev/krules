from app_functions.restapiclient import DoPostApiCall


class PostExtApi(DoPostApiCall):

    def execute(self, **kwargs):

        super().execute(
            "/device_manager/location_tracker",
            json={
                "owner": self.subject.get_ext("fleet"),
                "device": self.subject.name.split(":")[2],
                "location": kwargs.pop("location"),
                "coords": kwargs.pop("coords"),
                "timestamp": kwargs.pop("timestamp"),
            },
            raise_on_error=True,
            **kwargs
        )
