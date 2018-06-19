var element = undefined;


function update_barcode(element, value){
    JsBarcode(element, value, {
        format: "CODE128",
        displayValue: false,
        margin: 0
    });
}

function get_supplier_url(element_supplier){
	if (element_supplier.url && element_supplier.url.length > 3){
		return element_supplier.url
	}
	switch(element_supplier.supplier){
		case 'TME':
			return "https://www.tme.eu/cz/details/"+(element_supplier.symbol.replace('/', '_') || "Err");
			break;
		default:
			return null;
			break;
	}

}

// NASTAVENI MODALU PRO UPRAVU POLOZKY
function OpenArticleEdit(name = null){
    if (name === null){name = product_json['_id']}
    element = undefined;
    $('#modal-edit-component').modal('show');
    $('#inputCATEGORY_edit').select2({ width: '100%' });
    $('#new_supplier_name').select2({
        width: '100%',
        tags: true,
        multiple: true,
        maximumSelectionLength: 1,
        ajax: {
          url: '/store/api/get_suppliers/',
          type: "POST",
          dataType: 'json',
          processResults: function (data) {
              console.log(data)
              return {
                  results: $.map(data, function (item) {
                      console.log(item);
                      return {
                          text: item,
                          id: item
                      }
                  })
              };
          }
        }
    })

    try {
        $.ajax({
            type: "POST",
            url: "/store/api/product/",
            data: {
                'type':'filter',
                'key':'_id',
                'value': name,
                //'selected': active_categories(),
                //'polarity': $('#category_polarity').is( ":checked" )
            },
            success: function( data, textStatus, jQxhr ){
                element = data[0]
                element_stock = data[1]
                console.log(element);

                JsBarcode("#edit_barcode",element['_id'], {
                    format: "CODE128",
                    displayValue: false,
                    margin: 0
                });

                if (element == undefined){
                    Lobibox.notify('warning', {
                        title: 'Neznámá položka',
                        msg: 'Položka s tímto ID ještě není zadána ve skladu. Pokračováním vytvoříte novou položku.',
                        delay: 5000,
                        icon: false
                    });
                    product_json = {
                        '_id': id,
                        'name': id,
                        'stock':{},
                        'price':0,
                        'description':'',
                        'category': [],
                    }
                    return 0;
                }

                $('#inputID_edit').val(element['_id']);
                $("#inputID_edit").attr('disabled', true);
                $('#inputNAME_edit').val(element.name || "Bez názvu");
                //$('#inputPRICE_edit').val(element.price || 0);
                $('#inputPRICEp_edit').val(element.price_sell || 0);
                $('#inputSELLABLE_edit').prop('checked', element.sellable || false);
                $('#inputDESCRIPTION_edit').val(element.description || "");
                $('#inputCATEGORY_edit').val(element['category']).trigger('change');
                $('#inputSTOCK_list').empty();

                $('#new_param_name')[0].value = "";
                $('#new_param_value')[0].value = "";

                $('#new_supplier_code')[0].value = "";
                $('#new_supplier_symbol')[0].value = "";
                $('#new_supplier_url')[0].value = "";

                draw_parameters();
                draw_supplier();
                draw_stock(element_stock);
                draw_tags();

                //draw_stock(element['id']);
                draw_history(element['_id']);

            },
            error: function( jqXhr, textStatus, errorThrown ){
                console.log( errorThrown );
                Lobibox.notify('error', {
                    msg: 'Načtení položky neproběhlo úspěšně: ' + errorThrown,
                    icon: false,
                });
            }
        });

    }catch(err){
        alert("načítání se nezdařilo. Pro více informací navštivte konzoli... :-( Omlouvám se...");
    }
}

function ClearArticleEdit(){
    $('#inputID_edit').val("");
    $("#inputID_edit").attr('disabled', false);
    $('#inputNAME_edit').val("");
    $('#inputPRICE_edit').val(0);
    $('#inputPRICEp_edit').val(0);
    $('#inputSELLABLE_edit').prop('checked', false);
    $('#inputDESCRIPTION_edit').val("");
    $('#inputCATEGORY_edit').val(null).trigger('change');
    $('#inputTAG_edit').val(null).trigger('change');

    $('#new_param_name')[0].value = "";
    $('#new_param_value')[0].value = "";

    $('#new_supplier_code')[0].value = "";
    $('#new_supplier_symbol')[0].value = "";
    $('#new_supplier_url')[0].value = "";

    draw_parameters();
    draw_stock();
    draw_history();
    draw_supplier();
}

function UpdateFromForm(){
    element['_id'] = $('#inputID_edit')[0].value;
    element.name = $('#inputNAME_edit')[0].value;
    element.description=$('#inputDESCRIPTION_edit')[0].value;
    element.sellable = $('#inputSELLABLE_edit').prop('checked');
    //element.price = Number($('#inputPRICE_edit')[0].value);
    element.price_sell = Number($('#inputPRICEp_edit')[0].value);
    element.category = $('#inputCATEGORY_edit').val();

    tags = [];
    for (tag in $('#inputTAG_edit').val()){
        tags = tags.concat( {'id': $('#inputTAG_edit').val()[tag]} );
        console.log([{'id': $('#inputTAG_edit').val()[tag]}]);
    }
    console.log(tags);
    element['tags'] = tags;
    console.log(element);
}

function WriteToDb(){
    UpdateFromForm();
    $.ajax({
        type: "POST",
        url: "/store/api/update_product/",
        data: {json: JSON.stringify(element)},
        success: function( data, textStatus, jQxhr ){
            console.log(textStatus);
            Lobibox.notify('success', {
                msg: 'Polozka uspesne ulozena: ' + textStatus,
                icon: false,
            });
            $('#modal-edit-component').modal('hide');
        },
        error: function( jqXhr, textStatus, errorThrown ){
            console.log( errorThrown );
            Lobibox.notify('error', {
                msg: 'Ukladani nove polozky nebylo uspesne: ' + errorThrown,
                icon: false,
            });
        }
    });
}

function add_parameter(){
  if ((element.parameters || []).length < Number($('#new_param_id')[0].value)){
    if (element.parameters === undefined){
        console.log("Toto jeste neni definovane");
        element.parameters = [];
    }
    var nid = element.parameters.push({
        "name":$('#new_param_name')[0].value,
        "value":$('#new_param_value')[0].value
    });
  }
  else {
    element.parameters[Number($('#new_param_id')[0].value)-1]={
        "name":$('#new_param_name')[0].value,
        "value":$('#new_param_value')[0].value
    };
  }

  $("#new_param_id")[0].value = (element.parameters || []).length+1;
  draw_parameters();
}

function rm_parameter(id){
    element.parameters.splice(id, 1);
    draw_parameters();
}

function move_param(id, dir){
    var move = element.parameters[id];
    element.parameters.splice(id, 1);
    element.parameters.splice(id+dir, 0, move);
    draw_parameters();
}

function draw_parameters(){
  var parameters = element.parameters;

  if (parameters === undefined || parameters == {} || Array.isArray(parameters) == false){
    parameters = [];
    $("#new_param_id")[0].value = 1;
  }
  $("#param_table_body").empty();
  console.log("All", parameters);

  for (param in parameters){
    var p = parameters[param];

    var html = "<tr><td>" + (Number(param)+1).toString() + "</td><td>" + p.name + "</td><td>"+ p.value +
      "</td><td style='padding: 0pt;'>"+
      "<div class='btn-group' role='group'>"+
      "<button class='btn btn-sm btn-outline-primary' onclick='edit_param("+param+")'><i class='material-icons'>edit</i></button>" +
      "<button class='btn btn-sm btn-outline-success' onclick='move_param("+param+", -1)'><i class='material-icons'>keyboard_arrow_up</i></button>" +
      "<button class='btn btn-sm btn-outline-success' onclick='move_param("+param+", +1)'><i class='material-icons'>keyboard_arrow_down</i></button>" +
      "<button class='btn btn-sm btn-outline-danger'  onclick='rm_parameter("+param+")'><i class='material-icons'>delete_forever</i></button></td></tr>"+
      "</div>";
    console.log(html);
    $("#param_table_body").append(html);
  }
  element.parameters = parameters;
}




function add_supplier(){
  var data = {
        "supplier":$('#new_supplier_name').val()[0],
        "symbol": $('#new_supplier_symbol')[0].value,
        "barcode":$('#new_supplier_code')[0].value,
        "bartype":$('#new_supplier_bartype')[0].value,
        "url":$('#new_supplier_url')[0].value
  };
  if ((element.supplier || []).length < Number($('#new_supplier_id')[0].value)){
      if (element.supplier === undefined){
          console.log("Toto jeste neni definovane");
          element.supplier = [];
      }
      var nid = element.supplier.push(data);
  } else {
      element.supplier[Number($('#new_supplier_id')[0].value)-1] = data;
  }
    $("#new_supplier_id")[0].value = (element.supplier).length+1;
    draw_supplier();
    $('#collapseOne').collapse('hide');

    $('#new_supplier_name').val(null).trigger('change');
    $('#new_supplier_id')[0].value = id+1
    $('#new_supplier_symbol')[0].value = '';
    $('#new_supplier_code')[0].value = '';
    $('#new_supplier_bartype')[0].value = '';
    $('#new_supplier_url')[0].value = '';
}

function rm_supplier(id){
    //element.supplier.splice(id, 1);
    if(!!element.supplier[id].disabled && element.supplier[id].disabled == 1){
        element.supplier[id]['disabled'] = 0;
    }else{
        element.supplier[id]['disabled'] = 1;
    }
    draw_supplier();
}

function ed_supplier(id){
    //$('#new_supplier_name').val(null).trigger('change');
    $('#new_supplier_name').val(null).append(new Option(element.supplier[id].supplier, element.supplier[id].supplier, true, true)).trigger('change');
    $('#new_supplier_id')[0].value = id+1;
    $('#new_supplier_symbol')[0].value = (element.supplier[id].symbol) || '';
    $('#new_supplier_code')[0].value = (element.supplier[id].barcode) || '';
    $('#new_supplier_bartype')[0].value = (element.supplier[id].bartype) || '';
    $('#new_supplier_url')[0].value = (element.supplier[id].url) || '';
    $('#collapseOne').collapse('show');
}

function draw_supplier(){
  var parameters = element.supplier || [];
  $("#inputSUPPLIER_list").empty();
  $("#new_supplier_id")[0].value = (element.supplier).length+1;
  for (param in parameters){
    var p = parameters[param];

    var html = "<div class='card p-2 m-0 mt-1 row' >"+
                "<div class='col-auto mr-auto'><span>"+ "#"+(Number(param)+1).toString()+ "  "+
                p.supplier + "</span> - "+
                "<span>"+ p.symbol + "</span></div>"+
                "<div class='btn-group btn-group-justified col-auto'>"+
                "<a class='btn btn-sm btn-outline-success' onclick='ed_supplier("+param+")'><i class='material-icons'>edit</i></a>"+
                "<a class='btn btn-sm btn-outline-primary' href='" + p.url + "' target='_blank' ><i class='material-icons'>link</i></a>"+
                "<a class='btn btn-sm btn-outline-danger' onclick='rm_supplier("+param+")'><i class='material-icons isrm'></i></a></div>"+
                "</div>";
    var $html = $('<div />',{html:html});
    
    if((p.disabled || 0) == 1){
        $html.find('.card').addClass('text-muted');
        $html.find('.card').addClass('bg-light');
        $html.find('.isrm').html('check_circle_outline');
    }else{
        $html.find('.card').addClass('bg-light');
        $html.find('.isrm').html('highlight_off');
    }

    $("#inputSUPPLIER_list").append($html.html());

  }
}

function draw_stock(count){
  //var parameters = element.stock || {};
  $("#inputSTOCK_list").empty();
  //console.log("STOCK", parameters);

  for (param in count){
    var c = count[param];
    console.log(c);
    var num = c.bilance || 'Ndef';
    if (permis == 0){
        if(num > 100){
            num = '100+';
        } else if(num > 10){
            num = '10+';
        } else {
            num = num;
        }
    }
    var html = "<div class='card m-0 p-2 mr-2'>"+ c._id + "<br>" + num +" units </div>";
    console.log(html);
    $("#inputSTOCK_list").append(html);

  }
}

function draw_tags(){
    $("#inputTAG_edit").select2({
        tags: true,
        width: '100%',
        ajax: {
          url: '/store/api/get_tags/',
          type: "POST",
          dataType: 'json',
          processResults: function (data) {
              console.log(data)
              return {
                  results: $.map(data, function (item) {
                      console.log(item);
                      return {
                          text: item,
                          id: item
                      }
                  })
              };
          }
        }
        //tokenSeparators: [',', ' '],
    });
    $('#inputTAG_edit').val(null)
    for (i in element.tags || []){
        tag = element.tags[i];
        console.log(tag);
        $('#inputTAG_edit').append(new Option(tag.id, tag.id, true, true));
    }
    $('#inputTAG_edit').trigger('change');
}


function draw_history(id){
    $('#inputHISTORY_edit').empty();
    $.ajax({
        type: "POST",
        url: "/store/api/get_history/",
        data: {
            'key':id,
            'output': 'html_tab'
        },
        success: function( data, textStatus, jQxhr ){
            $("#inputHISTORY_edit").html(data);

        }
    });
}



function new_component(){

    $('#modal-edit-component').modal('show');
    $('#inputCATEGORY_edit').select2({ width: '100%' });

    element = {};

    ClearArticleEdit();
}
