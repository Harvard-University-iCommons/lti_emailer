(function(){
    var app = angular.module('mailingList', ['ngSanitize', 'ngAnimate', 'ng.django.urls']).config(function($httpProvider){
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
        var GET_COURSE = $djangoUrl.reverse('mailing_list:api_course');

        ml.isLoading = true;
        ml.isUpdating = false;
        ml.primarySectionLists = [];
        ml.otherSectionLists = [];
        ml.course_code = null;
        // temp storage for modal interaction to access level to prevent base
        // page from updating until the requested change has been saved via AJAX
        ml.updatedAccessLevel = '';
        ml.accessLevels = [{
            id: 'staff',
            name: {class: 'Staff Access:', section: 'Staff Access:'},
            description: {
                class: 'staff can email members of this course; students and guests <strong>cannot</strong> send or reply to this mailing list.',
                section: 'staff can email members of this course; students and guests <strong>cannot</strong> send or reply to this mailing list.'
            }
        },{
            id: 'members',
            name: {class: 'Course Access:', section: 'Section Access:'},
            description: {
                class: 'all members of this course can email each other; students and guests <strong>can</strong> send and reply to this mailing list.',
                section: 'all members of this section and all staff can email each other; students and guests <strong>can</strong> send and reply to this mailing list.'
            }
        },{
            id: 'everyone',
            name: {class: 'World Access:', section: 'World Access:'},
            description: {
                class: 'anyone can send and reply to this mailing list.',
                section: 'anyone can send and reply to this mailing list.'
            }
        },{
            id: 'readonly',
            name: {class: 'Disabled:', section: 'Disabled:'},
            description: {
                class: 'this mailing list is disabled.',
                section: 'his mailing list is disabled.'
            }
        }];
        ml.accessLevelDisplayNameMap = {};
        ml.accessLevelDescriptionMap = {};
        for (var i = 0; i < ml.accessLevels.length; i++) {
            var accessLevel = ml.accessLevels[i];
            ml.accessLevelDisplayNameMap[accessLevel.id] = accessLevel.name;
            ml.accessLevelDescriptionMap[accessLevel.id] = accessLevel.description;
        }

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

        $http.get(GET_COURSE).success(function(data){
            ml.course_code = data.course_code;
        });

        ml.hasPrimarySections = function() {
            return ml.primarySectionLists.length > 0;
        };

        ml.hasOtherSections = function() {
            return ml.otherSectionLists.length > 0;
        };

        ml.updateAccessLevel = function(list) {
            $('#permissions-modal-' + list.section_id).modal('hide');
            list.isUpdating = true;
            var url = $djangoUrl.reverse(
                'mailing_list:api_lists_set_access_level',
                [list.id]
            );
            $http.put(url, {access_level: ml.updatedAccessLevel})
                .success(function(data){
                    list.access_level = ml.updatedAccessLevel;
                    list.isUpdating = false;
                    list.updated = true;
                    $timeout(function(){
                        list.updated = false;
                    }, 2000);
                }).error(function(data){
                    list.isUpdating = false;
                    list.update_failed = true;
                    $timeout(function(){
                        list.update_failed = false;
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
