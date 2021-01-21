if (typeof jQuery !== 'undefined' || typeof(django.jQuery) !== 'undefined') {
(function($){

$( window ).on('load', function(e) {
    const widgets = $('.jsonwidget');
    const parsed_areas = widgets.find('div.parsed');
    parsed_areas.JSONView('collapse');
    $('.parseraw').remove();
    widgets.find('textarea').remove();
});
})((typeof jQuery !== 'undefined') ? jQuery : django.jQuery);
} else {
  throw new Error('django-krules-procevents requires jQuery');
}
