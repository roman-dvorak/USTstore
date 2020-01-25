

Lobibox.base.DEFAULTS = $.extend({}, Lobibox.base.DEFAULTS, {
	soundPath: '/static/lobibox/sounds/'
});

Lobibox.notify.DEFAULTS = $.extend({}, Lobibox.notify.DEFAULTS, {
	soundPath: '/static/lobibox/sounds/'
});

$.fn.select2.defaults.set( "theme", "bootstrap" );

var stocks_info = []

function get_stocks(){
	$.ajax({
        type: "POST",
        url: "/store/api/get_warehouses/",
        data: {
        },
        success: function( data, textStatus, jQxhr ){
       		console.log(data);
       		stocks_info = data;
        },
        error: function(data, status){
        	alert("Sklady nebyly nacteny");
        }
})
}

function get_stock(id){
	return stocks_info.filter(s => s._id.$oid == id);
}

function get_current_stock(){
	return Cookies.get("warehouse");
}

get_stocks();
