document.addEventListener('DOMContentLoaded', () => {
    'use strict';

    let buffer = '';

    document.addEventListener('keydown', event => {
        const charList = 'abcdefghijklmnopqrstuvwxyz0123456789_';
        const key = event.key
        // no key logging if modal is opened
        if (document.body.classList.contains('modal-open') == false) {
            if (key === "Enter"){
                const url = '/consumables/'.concat(buffer);
                window.open(url, "_self");
                buffer = '';
            }
    
            // we are only interested in alphanumeric keys
            if (charList.indexOf(key) === -1) return;
    
            buffer = buffer.concat(key);
            // console.log(buffer);
        }
        
    });
});