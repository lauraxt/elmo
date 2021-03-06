/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is l10n django site.
 *
 * The Initial Developer of the Original Code is
 *   Mozilla Foundation.
 * Portions created by the Initial Developer are Copyright (C) 2011
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *   Peter Bengtsson <peterbe@mozilla.com>
 *
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 *
 * ***** END LICENSE BLOCK ***** */

var dropMode = null;
function dropDiff(event, ui) {
  $(this).append(ui.draggable);
  ui.draggable.css('top', 0);
}

$(document).ready(function() {
  $('.diffanchor').draggable({
     appendTo: 'body',
    axis: 'y',
    revert: true,
    start: function(event, ui) {
      if (dropMode != 'diff') {
        $('.ui-droppable').droppable('destroy');
        $('.diff').droppable({
           drop: dropDiff
        });
        dropMode = 'diff';
      }
    }
  });

  $('.diff').click(function(event) {
    event.stopPropagation();
    var dfs = $('.diffanchor').parent().prev().find('.shortrev');
    if (dfs.length < 2 || dfs[0].textContent == dfs[1].textContent) return;
    var params = {
      to: dfs[0].textContent,
      from: dfs[1].textContent,
      tree: diffData.tree,
      repo: diffData.repo,
      url: '',
      locale: diffData.locale
    };
    params = $.param(params);
    window.open(diffData.url + params);
  });

  function hoverSO(showOrHide) {
    return function() {
      var q = $('#so_' + this.getAttribute('data-push'))
        .not('.suggested')
          .not('.clicked');
      if (showOrHide === 'hide') {
        q.addClass('hidden');
      } else {
        q.removeClass('hidden');
      }
    }
  }

  $('.pushrow').hover(hoverSO('show'), hoverSO('hide'))
    .click(function() {
      var self = $(this);
      var so = $('#so_' + this.getAttribute('data-push'))
        .not('.suggested');
      if (! so.length) { return; }
      var wasClicked = so.hasClass('clicked');
      so.toggleClass('clicked');
      // XXXX, guess what touch would do
      if (wasClicked != so.hasClass('hidden')) {
        so.toggleClass('hidden');
      }
    });

  if (permissions && permissions.canAddSignoff) {
    $('input.do_signoff').click(doSignoff);
    $('#add_signoff').dialog({
      autoOpen: false,
      width: 600,
      minWidth: 300,
      title: 'Sign-off'
    });
  }
  if (permissions && permissions.canReviewSignoff) {
    $('#review_signoff').dialog({
      autoOpen: false,
      width: 600,
      minWidth: 300,
      title: 'Review'
    });
    $('.review_action').click(function(event) {
      var signoff_id = event.target.getAttribute('data-signoff');
      var rs = $('#review_signoff');
      rs.children('form')[0].signoff_id.value = signoff_id;
      rs.dialog('open');
    });
  }
});

var Review = {
   accept: function(event) {
     var frm = event.target.form;
     frm.querySelector('[type=submit]').disabled = false;
     frm.comment.disabled = true;
     frm.clear_old.disabled = true;
   },
  reject: function(event) {
    var frm = event.target.form;
    frm.querySelector('[type=submit]').disabled = false;
    frm.comment.disabled = false;
    frm.clear_old.disabled = false;
    frm.comment.focus();
  }
};

function showSignoff(details_content) {
  $('#signoff_desc').html(details_content);
  $('#add_signoff').dialog('open');
}

function doSignoff(event) {
  event.stopPropagation();
  var t = $(event.target);
  var rev = event.target.id.substr(3);
  var sf = $('#signoff_form');
  sf.children('[name=revision]').val(rev);
  var run = t.attr('data-run');
  sf.children('[name=run]').val(run);
  $.get(signoffDetailsURL, {rev: rev, run: run}, showSignoff, 'html');
}
