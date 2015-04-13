(function(){
    var app = angular.module('mailingList', ['ng.django.urls']).config(function($httpProvider){
        $httpProvider.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';
        $httpProvider.defaults.xsrfCookieName = 'csrftoken';
        $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';
    });

    app.controller('MailingListController', ['$http', 'djangoUrl', function($http, $djangoUrl){
        var ml = this;
        var URL_LISTS = $djangoUrl.reverse('mailing_list:api_lists', [window.globals.RESOURCE_LINK_ID]);

        ml.mailingLists = [];

        $http.get(URL_LISTS).success(function(data){
            ml.mailingLists = data;
        });

        ml.toggleActive = function(list) {
            var url = $djangoUrl.reverse('mailing_list:api_lists_set_active', [list.id, window.globals.RESOURCE_LINK_ID]);
            $http.put(url, {active: !list.active}).success(function(data){
                list.active = data.active
            });
        }
    }]);
})();
