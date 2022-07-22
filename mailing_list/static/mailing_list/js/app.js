(function(){
  var app = angular.module('mailingList', ['ngSanitize', 'ngAnimate', 'djng.urls']).config(function($httpProvider){
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

  app.controller('MailingListController',
      ['$http', '$timeout', 'djangoUrl', '$q',
      function($http, $timeout, djangoUrl, $q){
    var ml = this;
    var URL_LISTS = djangoUrl.reverse('mailing_list:api_lists');
    var URL_SETTINGS = djangoUrl.reverse('mailing_list:api_course_settings');

    ml.alerts = {
      course: {
        settingsUpdated: {
          true: {
            type: 'alert-success',
            message: 'From now on, any email sent to a section will be delivered to members of that section <strong>and to all staff in the course</strong>.'
          },
          false: {
            type: 'alert-success',
            message: 'From now on, any email sent to a section will be delivered <strong>only to members of that section</strong>.'
          },
          failure: {
            type: 'alert-danger',
            message: 'Your setting was not applied. Please try again.'
          }
        }
      }
    };
    ml.courseSettings = {
      alert: null,
      isUpdating: false,
      formValues: null,  // stores values displayed by UI
      values: null  // stores server-sourced values
    };
    ml.isLoading = true;
    ml.isUpdating = false;
    ml.courseList = [];
    ml.enrollmentSectionLists = [];
    ml.nonEnrollmentSectionLists = [];
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
      id: 'readonly',
      name: {class: 'Disabled:', section: 'Disabled:'},
      description: {
        class: 'this mailing list is disabled.',
        section: 'this mailing list is disabled.'
      }
    }];
    ml.accessLevelDisplayNameMap = {};
    ml.accessLevelDescriptionMap = {};
    for (var i = 0; i < ml.accessLevels.length; i++) {
      var accessLevel = ml.accessLevels[i];
      ml.accessLevelDisplayNameMap[accessLevel.id] = accessLevel.name;
      ml.accessLevelDescriptionMap[accessLevel.id] = accessLevel.description;
    }

    var listsPromise = $http.get(URL_LISTS).success(function(data){
      var length = data.length;
      var course_list_member_count = 0;
      var list;

      for (var i = 0; i < length; i++) {
        list = data[i];
        if(list.is_course_list) {
          ml.courseList.push(list);
          course_list_member_count = list.members_count;
        } else if(!list.sis_section_id || list.cs_class_type == 'N'){
          ml.nonEnrollmentSectionLists.push(list);
        } else if(list.sis_section_id || list.cs_class_type == 'E'){
          ml.enrollmentSectionLists.push(list);
        }
      }
    });

    var settingsPromise = $http.get(URL_SETTINGS)
      .then(function getCourseSettingsSuccess(response) {
        ml.courseSettings.values = angular.copy(response.data);
        ml.courseSettings.formValues = angular.copy(response.data);
      });

    $q.all([listsPromise, settingsPromise]).then(function initialDataLoaded() {
      ml.isLoading = false;
      ml.loaded = true;
    });

    ml.hasCourseEmailList = function(){
      return ml.courseList.length > 0;
    };

    ml.hasMultipleSections = function() {
      // returns true if there are any sections other than the primary section
      // (which contains the full course enrollment, teachers + students)
      return ml.hasMultipleEnrollmentSections() || ml.hasNonEnrollmentSections();
    };

    ml.hasMultipleEnrollmentSections = function() {
      // All courses have at least one section, the primary section (which
      // corresponds to the full course enrollment list for the primary course)
      // This returns true if there are other registrar-fed or secondary
      // cross-listed sections.
      return ml.enrollmentSectionLists.length > 1;
    };

    ml.hasNonEnrollmentSections = function() {
      // Returns true if course is associated with manually created sections
      // (Canvas-only sections created using Canvas section tool or Harvard
      // Manage Sections tool)
      return ml.nonEnrollmentSectionLists.length > 0;
    };

    ml.isNonEnrollmentSectionsList = function(list){
      return (list.cs_class_type == 'N');
    };

    ml.isManageSectionsList = function(list){
      return list.sis_section_id == null && ! list.is_course_list;
    };

    ml.updateAccessLevel = function(list) {
      $('#permissions-modal-' + list.section_id).modal('hide');
      list.isUpdating = true;
      var url = djangoUrl.reverse(
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

    ml.updateCourseSettings = function() {
      ml.courseSettings.isUpdating = true;
      $http.put(URL_SETTINGS, ml.courseSettings.formValues)
        .then(function putCourseSettingsSuccess(response) {
          ml.courseSettings.values = angular.copy(response.data);
          ml.courseSettings.formValues = angular.copy(response.data);
          ml.courseSettings.alert = ml.alerts.course.settingsUpdated[response.data.always_mail_staff];
        }, function putCourseSettingsFailure(response) {
          ml.courseSettings.formValues = angular.copy(ml.courseSettings.values);
          ml.courseSettings.alert = ml.alerts.course.settingsUpdated.failure;
        }).finally(function putCourseSettingsFinally(response) {
          ml.courseSettings.isUpdating = false;
        });
    };

    ml.listMembersUrl = function(list) {
      if(list.section_id) {
        return window.globals.append_resource_link_id(
          djangoUrl.reverse('mailing_list:list_members',
          [list.section_id]));
      }else{
        return window.globals.append_resource_link_id(
          djangoUrl.reverse('mailing_list:list_members_no_id'));
      }
    };

    ml.showSettings = function() {
      return (ml.courseSettings.formValues && ml.hasMultipleSections());
    };

    if(window.location.href.indexOf("local") !== -1) {
      var msg = "Members count may not reflect mailing list in non-production. An intersection of the email lists is being done to prevent accidently emailing users.";
      setTimeout(function () { alert(msg); }, 5000);
      console.log(msg);
    };

  }]);
})();
