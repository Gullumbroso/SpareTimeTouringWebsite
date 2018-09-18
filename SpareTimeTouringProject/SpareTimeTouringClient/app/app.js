/**
 * Created by gullumbroso on 07/12/2016.
 */

angular.module('SpareTimeTouring', ['ngMaterial', 'moment-picker'])

    .config(function ($mdThemingProvider) {
        $mdThemingProvider.theme('default')
            .primaryPalette('blue-grey', {
                'default': '900'
            })
            .accentPalette('pink', {
                'default': '500'
            })
    })

    .run([
        function () {

            // global constants

        }])

    .directive('googleplace', function ($rootScope) {
        return {
            require: 'ngModel',
            scope: {
                ngModel: '=',
                details: '=?'
            },
            link: function (scope, element, attrs, model) {
                var options = {
                    types: [],
                    componentRestrictions: {}
                };
                scope.gPlace = new google.maps.places.Autocomplete(element[0], options);

                google.maps.event.addListener(scope.gPlace, 'place_changed', function () {
                    var geoComponents = scope.gPlace.getPlace();
                    var latitude = geoComponents.geometry.location.lat();
                    var longitude = geoComponents.geometry.location.lng();
                    scope.$apply(function () {
                        if (attrs.id === "curLoc")
                            $rootScope.curLoc = [latitude, longitude];
                        else
                            $rootScope.dest = [latitude, longitude];
                        model.$setViewValue(element.val());
                    });
                });
            }
        };
    })

    .controller('SpareTimeTouringController', function ($scope, $rootScope, $http, $timeout, $mdDialog) {

        var DEFAULT_BUTTON_TITLE = "Start";
        var AGAIN_BUTTON_TITLE = "New Search";
        var AWAITING_INPUT_STATUS = "awaiting";
        var LOADING_STATUS = "loading";
        var ANSWERED_STATUS = "answered";
        var BASE_URL = "http://127.0.0.1:8000";
        var APP_PATH = "/best_route/";

        $scope.query = {};
        $scope.noCache = true;

        $scope.status = AWAITING_INPUT_STATUS;
        $scope.goTitle = DEFAULT_BUTTON_TITLE;
        $scope.tryAgainTitle = AGAIN_BUTTON_TITLE;
        $scope.presentResults = false; // For animation;
        $scope.content = "";
        $scope.answer = "";
        $scope.article = {
            title: "",
            content: ""
        };

        $scope.selectedItem = null;
        $scope.sourceText = null;
        $scope.destinationText = null;

        $scope.query.start = "";
        $scope.query.destination = "";
        $scope.query.arrivalTime = "";
        this.ctrl = {timepicker: ""};

        function presentAlertDialog(title, content, ev) {
            $mdDialog.show(
                $mdDialog.alert()
                    .parent(angular.element(document.body))
                    .clickOutsideToClose(true)
                    .title(title)
                    .textContent(content)
                    .ariaLabel('Alert Dialog')
                    .ok("OK")
                    .targetEvent(ev)
            );
        }

        $scope.go = function (event) {

            if ($scope.status === AWAITING_INPUT_STATUS) {

                if ($scope.status === LOADING_STATUS) return;

                if (!this.ctrl) {
                    this.ctrl = {timepicker: ""};
                }
                $scope.query.arrivalTime = this.ctrl.timepicker;
                if ($scope.query.start === "" || $scope.query.destination === "" || $scope.query.arrivalTime === "" || !$scope.query.arrivalTime) {
                    presentAlertDialog("Invalid input", "Please fill all the fields.", event);
                    return;
                }

                var startName = $scope.query.start;
                var startLoc = $rootScope.curLoc;

                var start = {
                    name: startName,
                    lat: startLoc[0],
                    lon: startLoc[1]
                };

                var destinationName = $scope.query.destination;
                var destinationLoc = $rootScope.dest;

                var destination = {
                    name: destinationName,
                    lat: destinationLoc[0],
                    lon: destinationLoc[1]
                };

                var now = new Date();
                var arrivalTimeString = $scope.query.arrivalTime;
                arrivalTimeString = arrivalTimeString.split(':');
                var hours = parseInt(arrivalTimeString[0]);
                var minutes = parseInt(arrivalTimeString[1]);
                var arrivalTime = new Date();
                arrivalTime.setHours(hours);
                arrivalTime.setMinutes(minutes);

                if (arrivalTime < now) {
                    presentAlertDialog("Invalid Arrival Time", "Please enter a future arrival time.", event);
                    return;
                }

                var url = BASE_URL + APP_PATH;
                var params = {
                    start: start,
                    dest: destination,
                    arrival_time: $scope.query.arrivalTime
                };
                $scope.status = LOADING_STATUS;
                $http.get(url, {params: params})
                    .then(function (response) {
                            // success
                            var dictRoute = response.data['route'];
                            $scope.route = [];
                            for (var i = 1; i < dictRoute.length - 1; i++) {
                                $scope.route.push({
                                    venue: dictRoute[i]['venue'],
                                    duration: dictRoute[i]['duration'] / 3600
                                })
                            }

                            $scope.duration = response.data['duration'];
                            $scope.score = response.data['score'];
                            $scope.status = ANSWERED_STATUS;
                            $scope.goTitle = AGAIN_BUTTON_TITLE;
                            $timeout(function () {
                                $scope.presentResults = true;
                            }, 500);
                        },
                        function (err) {
                            // error
                            $scope.status = ANSWERED_STATUS;
                            $scope.answer = "Something went wrong, please try again.";
                            $scope.resultIcon = "assets/StarTypeLogo_PROBLEM.png";
                            $scope.confidence = "";
                            $scope.confidence_score = "";
                            $scope.url = "";
                            $scope.goTitle = AGAIN_BUTTON_TITLE;
                            $timeout(function () {
                                $scope.presentResults = true;
                            }, 500);
                        });
            }
        };

        $scope.tryAgain = function (event) {
            $scope.status = AWAITING_INPUT_STATUS;
            $scope.goTitle = DEFAULT_BUTTON_TITLE;
            $scope.presentResults = false;
        }
    });
