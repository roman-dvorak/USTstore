

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



function copyToCLipboard(el){
    console.log("COPY", el);
    var data = el.getAttribute('copy')
    var dummy = document.createElement("input");
    document.body.appendChild(dummy);
    dummy.setAttribute("value", data);
    dummy.select();
    document.execCommand("copy");
    document.body.removeChild(dummy);
    console.log("Copy", data);
}



var barcode_input_history = [];

function barcode_input(data){
  var element = barcode_input_history.pop();
	console.log("Barcode inpur", element);
  $(element).val(data).trigger('change');
}

// virtualni nacteni kodu
$(document).on("click", ".barcode-value", function() {
      console.log("Dummy barcode reader", this);
      var data = $(this).attr('data');
      barcode_input(data);
});

$(document).on("focus", ".id_input", function() {
      console.log("ID input", this);
      barcode_input_history.push(this);
});
$(document).on('select2:opening', '.id_input', function () {
      console.log("ID input SELECT", this);
      barcode_input_history.push(this);
});
