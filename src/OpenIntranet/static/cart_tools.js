

function select_cart(id) {
	if(id != null){
		document.cookie = "cart="+id;
		console.log("Nákupní košík nastaven na:", id);
	}else{
		//TODO: smazat cookie
	}
}


function add_to_cart_count(cart, element){
	var polozka = cart || current_detail;
	var count = $(element)[0].value;

	console.log("Přidávám", polozka, "s poctem", count, element);
	$.ajax({
        type: "POST",
        url: "/cart/api/add_to_cart",
        data: {
            'id': polozka,
            'count': count
        },
        success: function( data, textStatus, jQxhr ){
       		
        },
        error: function(data, status){
        	alert("Polozka nebyla pridata");
        }
    });
}