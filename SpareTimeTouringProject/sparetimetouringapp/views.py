from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.response import Response
import sparetimetouringapp.services as services
import ast


class SpareTimeTouring(APIView):
    """
    The api endpoint for validating the received article.
    """

    def get(self, request):

        params = request.query_params
        if len(params) != 3:
            return Response("Please enter a valid input.", status=status.HTTP_204_NO_CONTENT)
        else:
            start = ast.literal_eval(params['start'])
            destination = ast.literal_eval(params['dest'])
            arrival_time_string = params['arrival_time']
            arrival_time = services.parse_time(arrival_time_string)
            route, duration, value = services.run_search(start, destination, arrival_time)

            # Parse route for json
            route_as_dicts = list({'venue':venue.name, 'duration':duration} for venue, duration in route)

            response = {
                'route': route_as_dicts,
                'duration': duration,
                'score': value,
            }

            return Response(response, status=status.HTTP_200_OK)
