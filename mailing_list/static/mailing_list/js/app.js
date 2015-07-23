(function(){
    var app = angular.module('mailingList', ['ngAnimate', 'ng.django.urls']).config(function($httpProvider){
        $httpProvider.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';
        $httpProvider.defaults.xsrfCookieName = 'csrftoken';
        $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';
        $httpProvider.interceptors.push(function(){
            return {
                'request': function(config){
                    // window.globals.append_resource_link_id function added by
                    // django_auth_lti/js/resource_link_id.js
                    config.url = window.globals.append_resource_link_id(config.url);
                    return config;
                }
            };
        });
    });

    app.controller('MailingListController', ['$http', '$timeout', 'djangoUrl', function($http, $timeout, $djangoUrl){
        var ml = this;
        var URL_LISTS = $djangoUrl.reverse('mailing_list:api_lists');

        ml.isLoading = true;
        ml.isUpdating = false;
        ml.primarySectionLists = [];
        ml.otherSectionLists = [];
        ml.accessLevels = [{
            id: 'members',
            name: 'Course Enrollees'
        },{
            id: 'staff',
            name: 'Course Staff'
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
            var url = $djangoUrl.reverse('mailing_list:api_lists_set_access_level', [list.id]);
            $http.put(url, {access_level: list.access_level}).success(function(data){
                list.isUpdating = false;
                list.updated = true;
                $timeout(function(){
                    list.updated = false;
                }, 2000);
            });
        };

        ml.listMembersUrl = function(list) {
            return window.globals.append_resource_link_id(
                       $djangoUrl.reverse('mailing_list:list_members',
                                          [list.section_id]));
        };
    }]);
})();
