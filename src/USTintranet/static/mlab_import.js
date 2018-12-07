function UpdateModule(module) {
	//alert(module);
	$.ajax({
		type: "POST",
		url: '/mlab_import/update',
		data: {'module': module},
		success: function(data, status){
        	alert(data);
    	}
		//dataType: dataType
	});

}