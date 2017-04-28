(function(){
	$('#login').submit(function(event) {
		var form = $(this);
		form.addClass('loading');
	});
	$(document).ready(function(){
    	$('.tabular.menu .item').tab({history:false});
	})
	$(".mail-selector").click(function(event) {
		var $this = $(this);
		var folder = $this.data('folder')
		var id = $this.data('id')
		$(".mail-area.active").addClass('hidden').removeClass('active');
		console.log(".mail-area#" + folder + "-" + id);
		$(".mail-area#" + folder + "-" + id).addClass('active').removeClass('hidden');
		event.preventDefault();
	});
})();