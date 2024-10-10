from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.request import Request
# Create your views here.


class HelloWorldView(APIView):
    def get(self, request: Request):
        return Response({'message': 'Hello, World!'}, 200)