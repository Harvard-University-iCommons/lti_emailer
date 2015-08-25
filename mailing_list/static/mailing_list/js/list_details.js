$(document).ready(function(){
    $('.list-student a').click(function(){
        $a = $(this);
        $ul = $a.closest('ul');
        LTIAnalytics.pushInteraction({
            action: 'click',
            entity_type: 'mailing_list_member_address',
            entity_value: {
                canvas_course_id: $ul.data('canvas_course_id'),
                section_id: $ul.data('section_id'),
                address: $.trim($a.html())
            }
        });
    });
});
