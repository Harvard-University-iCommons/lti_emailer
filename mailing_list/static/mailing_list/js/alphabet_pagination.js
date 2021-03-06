(function($){

    $.fn.alphabetPagination = function(settings){
        var pluginEle = this;
        var pluginEleID = '#' + $(pluginEle).attr('id');
        
        var $list = $(pluginEleID);
        var $tabs = $list.find('.nav-section-pagination a');
        
        $tabs.click(function(e){
            //gets the range to be selected
            var range = $(this).attr('class');
            //checks that the <a> does not have the disabled class
            if (!$(this).parent().hasClass('disabled')){
                //remove the active class from previous position
                $(this).parent().siblings().removeClass('active');
                //make active currently clicked range
                $(this).parent().addClass('active');

                //display the selected range
                hideNames(pluginEleID, range);
            }
            

        });

        function hideNames(parent, range){
            $allItems = $(parent + ' .list-student');
            
            //hide all
            $allItems.addClass('hide');
            //clean up the list so it starts fresh
            $allItems.removeClass('showSection');

            //show all students
            if ( range == 'viewAll' ){
                $allItems.removeClass('hide');
                $allItems.addClass('showSection');
            }else{
                //show only the desire range
                $(parent).find('li.' + range).removeClass('hide');
                $(parent).find('li.' + range).addClass('showSection');
            }

            rangeNames(pluginEleID, '.pagination-lti-range');

        }

        //default all range saved for latter use
        //assume that is a string
        var allRange = '';
        function rangeNames(ele, dom){
            //container for range 
            var $rangeContainer = $(ele + ' ' + dom);
            //save the range only if the var is empty
            if (allRange != ''){
                allRange = $rangeContainer.text()
            }

            var start = $( ele + " li.showSection > .studentName" ).first().text();
            var end = $( ele + " li.showSection > .studentName" ).last().text();

            var currentRange;
            //check to see if there is only one name by comparing if the
            //start and end are equal (i.e.) Roderick Morales == Roderick Morales
            if (start == end){
                currentRange = $rangeContainer.text(start.split(' ')[1]);
            }else{
                currentRange = $rangeContainer.text(start.split(' ')[1] + ' - ' + end.split(' ')[1]);
            }
        }

    }//.fn (end)
})(jQuery);
