(function() {
'use strict';

//Clear input fields
$(document).ready(function(){
   
	function cookiesEnabled() {
	    var enabled = Cookies.set('check', 'valid', { expires: 1 }) && Cookies.get('check') === 'valid';
	    if (enabled ===  true){
	    	Cookies.remove('check');
	    }
	    return enabled;
	}

	//Check if Cookies are disabled
	//Display Error message and disable any submit buttons
	if (cookiesEnabled() === false){
		$('#errorMessages').innerHTML = '<p><center><strong><font color="red">This application requires cookies, please enable cookies in your browser and try again.</strong></center></p></font>';
		$('#submitButton').disabled = true;
	}

    $('#searchinput').keyup(function(){
        $('#searchclear').toggle(Boolean($(this).val()));
    });
    $('#searchclear').toggle(Boolean($('#searchinput').val()));
    $('#searchclear').click(function(){
        $('#searchinput').val('').focus();
        $(this).hide();
    });

    $('#confirm-send').on('show.bs.modal', function(e) {
    	var type = $(e.relatedTarget).attr('data-id');
    	$('#alert_type').val(type);
    });

    $('#alertSubmit').click(function(){
       $('#alertForm').submit();
       $('#confirm-send').modal('toggle');
   });

    $('#textNumberInput').mask('(999) 999-9999');
    $('#callNumberInput').mask('(999) 999-9999');

    $('.phoneFormat').text(function(i, text) {
        text = text.replace(/(\d{3})(\d{3})(\d{4})/, '($1) $2-$3');
        return text;
    });


    $('#signupForm, #unsubscribeForm').submit(function() {
    	$('#textNumberInput').val($('#textNumberInput').mask());
    	$('#callNumberInput').val($('#callNumberInput').mask());
    });
    
    $('#signupForm, #unsubscribeForm, #notificationsForm, #addressForm, #confirmationForm').submit(function() {
    	//Disable submit button on first click
    	$('#submitButton').attr('disabled', true);
        return true;
    });

    $('#datetimepicker').datetimepicker({
    	minDate : moment(),
    	format: 'DD/MM/YYYY hh:mm A',
    	sideBySide: true,
    	allowInputToggle: true,
    	showClear: true,
    	showClose: true
    });

});

})();
