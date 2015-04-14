(function(){
    var app = angular.module('mailingList', ['ngAnimate', 'ng.django.urls']).config(function($httpProvider){
        $httpProvider.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';
        $httpProvider.defaults.xsrfCookieName = 'csrftoken';
        $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';
    });

    app.controller('MailingListController', ['$http', '$timeout', 'djangoUrl', function($http, $timeout, $djangoUrl){
        var ml = this;
        var URL_LISTS = $djangoUrl.reverse('mailing_list:api_lists', [window.globals.RESOURCE_LINK_ID]);

        ml.isLoading = true;
        ml.isUpdating = false;
        ml.primarySectionLists = [];
        ml.otherSectionLists = [];
        ml.accessLevels = [{
            id: 'members',
            name: 'Course Enrollees'
        },{
            id: 'everyone',
            name: 'Anyone'
        },{
            id: 'readonly',
            name: 'No One'
        }];

        $http.get(URL_LISTS).success(function(data){
            ml.isLoading = false;
            var length = data.length;
            for (var i = 0; i < length; i++) {
                var list = data[i];
                if (list.is_primary_section) {
                    ml.primarySectionLists.push(list);
                } else {
                    ml.otherSectionLists.push(list);
                }
            }
            ml.loaded = true;
        });

        ml.hasPrimarySections = function() {
            return ml.primarySectionLists.length > 0;
        };

        ml.hasOtherSections = function() {
            return ml.otherSectionLists.length > 0;
        };

        ml.updateAccessLevel = function(list) {
            list.isUpdating = true;
            var url = $djangoUrl.reverse('mailing_list:api_lists_set_access_level', [list.id, window.globals.RESOURCE_LINK_ID]);
            $http.put(url, {access_level: list.access_level}).success(function(data){
                list.isUpdating = false;
                list.updated = true;
                $timeout(function(){
                    list.updated = false;
                }, 2000);
            });
        };
    }]);
})();
