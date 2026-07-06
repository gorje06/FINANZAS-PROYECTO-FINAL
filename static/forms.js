(function () {
  function showError(input, errId, msg) {
    if (!input) return;
    input.classList.add('is-error');
    var el = document.getElementById(errId);
    if (el) {
      el.textContent = msg;
      el.classList.add('visible');
    }
  }

  function clearError(input, errId) {
    if (!input) return;
    input.classList.remove('is-error');
    var el = document.getElementById(errId);
    if (el) {
      el.textContent = '';
      el.classList.remove('visible');
    }
  }

  window.initPasswordToggle = function (checkboxId, fieldIds) {
    var cb = document.getElementById(checkboxId);
    if (!cb) return;
    var ids = Array.isArray(fieldIds) ? fieldIds : [fieldIds];
    cb.addEventListener('change', function () {
      var t = cb.checked ? 'text' : 'password';
      ids.forEach(function (id) {
        var f = document.getElementById(id);
        if (f) f.type = t;
      });
    });
  };

  window.bindRequiredForm = function (formId, rules) {
    var form = document.getElementById(formId);
    if (!form) return;
    form.addEventListener('submit', function (e) {
      var ok = true;
      Object.keys(rules).forEach(function (name) {
        var input = form.querySelector('[name="' + name + '"]');
        var rule = rules[name];
        var errId = 'err-' + name;
        clearError(input, errId);
        if (!input || !input.value.trim() || input.value.trim().length < (rule.min || 1)) {
          showError(input, errId, rule.msg);
          ok = false;
        }
      });
      if (!ok) e.preventDefault();
    });
  };

  window.bindRegisterForm = function (formId) {
    var form = document.getElementById(formId);
    if (!form) return;
    form.addEventListener('submit', function (e) {
      var ok = true;
      var u = form.querySelector('[name="username"]');
      var dni = form.querySelector('[name="dni_usuario"]');
      var p1 = form.querySelector('[name="password"]');
      var p2 = form.querySelector('[name="password_confirm"]');
      clearError(u, 'err-username');
      clearError(dni, 'err-dni');
      clearError(p1, 'err-password');
      clearError(p2, 'err-password2');
      if (!u || u.value.trim().length < 3 || u.value.trim().length > 50) {
        showError(u, 'err-username', 'El usuario debe tener entre 3 y 50 caracteres');
        ok = false;
      }
      if (!dni || !/^\d{8}$/.test(dni.value.trim())) {
        showError(dni, 'err-dni', 'El DNI debe tener exactamente 8 dígitos');
        ok = false;
      }
      if (!p1 || p1.value.length < 6) {
        showError(p1, 'err-password', 'La contraseña debe tener al menos 6 caracteres');
        ok = false;
      }
      if (!p2 || p2.value !== p1.value) {
        showError(p2, 'err-password2', 'Las contraseñas no coinciden');
        ok = false;
      }
      if (!ok) e.preventDefault();
    });
  };

  function isFieldVisible(input) {
    if (!input) return false;
    var el = input;
    while (el && el !== document.body) {
      var st = window.getComputedStyle(el);
      if (st.display === 'none' || st.visibility === 'hidden') return false;
      el = el.parentElement;
    }
    return true;
  }

  window.bindWizard = function () {
    var form = document.getElementById('wizard-form');
    var panels = document.querySelectorAll('.wizard-panel');
    var steps = document.querySelectorAll('.wizard-step');
    var btnPrev = document.getElementById('wizard-prev');
    var btnNext = document.getElementById('wizard-next');
    var btnSubmit = document.getElementById('wizard-submit');
    var current = 0;

    function validateWizardStep(step) {
      var panel = panels[step];
      if (!panel) return true;
      if (step === 1 && window.validateWizardVehicleStep) {
        return window.validateWizardVehicleStep();
      }
      var inputs = panel.querySelectorAll('input, select, textarea');
      var ok = true;
      var firstBad = null;
      inputs.forEach(function (input) {
        if (!isFieldVisible(input) || !input.required) return;
        if (!String(input.value).trim()) {
          input.classList.add('is-error');
          if (!firstBad) firstBad = input;
          ok = false;
          return;
        }
        if (!input.checkValidity()) {
          input.classList.add('is-error');
          if (!firstBad) firstBad = input;
          ok = false;
        } else {
          input.classList.remove('is-error');
        }
      });
      if (!ok && firstBad) firstBad.focus();
      return ok;
    }

    function showStep(n) {
      current = n;
      panels.forEach(function (p, i) { p.classList.toggle('active', i === n); });
      steps.forEach(function (s, i) {
        s.classList.toggle('active', i === n);
        s.classList.toggle('completed', i < n);
      });
      if (btnPrev) btnPrev.style.display = n === 0 ? 'none' : '';
      if (btnNext) btnNext.style.display = n === panels.length - 1 ? 'none' : '';
      if (btnSubmit) btnSubmit.style.display = n === panels.length - 1 ? '' : 'none';
    }

    if (btnPrev) btnPrev.addEventListener('click', function () { if (current > 0) showStep(current - 1); });
    if (btnNext) btnNext.addEventListener('click', function () {
      if (!validateWizardStep(current)) return;
      if (current < panels.length - 1) showStep(current + 1);
    });
    if (form) {
      form.addEventListener('submit', function (e) {
        for (var i = 0; i < panels.length; i++) {
          if (!validateWizardStep(i)) {
            e.preventDefault();
            showStep(i);
            return;
          }
        }
      });
    }
    showStep(0);
  };

  window.syncTipoTasa = function () {
    var tipo = document.getElementById('tipo_tasa');
    var wrapP = document.getElementById('wrap_periodo_tasa');
    var wrapC = document.getElementById('wrap_capitalizacion');
    if (!tipo) return;
    function sync() {
      var nom = tipo.value === 'Nominal';
      if (wrapP) wrapP.style.display = nom ? 'none' : '';
      if (wrapC) wrapC.style.display = nom ? '' : 'none';
    }
    tipo.addEventListener('change', sync);
    sync();
  };

  window.syncModalidadCredito = function () {
    var modalidad = document.getElementById('modalidad');
    var moneda = document.getElementById('moneda');
    var wrapBalon = document.getElementById('wrap_cuota_balon');
    var wrapTc = document.getElementById('wrap_tipo_cambio');
    var inputBalon = wrapBalon ? wrapBalon.querySelector('[name="cuota_balon_pct"]') : null;
    var inputTc = wrapTc ? wrapTc.querySelector('[name="tipo_cambio"]') : null;
    if (!modalidad) return;
    function sync() {
      var ci = modalidad.value === 'Compra Inteligente';
      if (wrapBalon) wrapBalon.style.display = ci ? '' : 'none';
      if (inputBalon) inputBalon.required = ci;
      var usd = moneda && moneda.value === 'Dólares';
      if (wrapTc) wrapTc.style.display = usd ? '' : 'none';
      if (inputTc) inputTc.required = !!usd;
    }
    modalidad.addEventListener('change', sync);
    if (moneda) moneda.addEventListener('change', sync);
    sync();
  };

  function formatSoles(amount) {
    return 'S/ ' + Number(amount).toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  window.openVehicleInfoModal = function (data) {
    if (!data) return;
    var modal = document.getElementById('vehicle-info-modal');
    if (!modal) return;
    var imgWrap = document.getElementById('vehicle-info-image-wrap');
    var title = document.getElementById('vehicle-info-title');
    var tags = document.getElementById('vehicle-info-tags');
    var desc = document.getElementById('vehicle-info-desc');
    var price = document.getElementById('vehicle-info-price');
    if (title) title.textContent = data.marca + ' ' + data.modelo;
    if (imgWrap) {
      imgWrap.innerHTML = data.imagen_url
        ? '<img src="' + data.imagen_url + '" alt="' + data.marca + ' ' + data.modelo + '" />'
        : '<div class="vehicle-info-placeholder">🚗</div>';
    }
    if (tags) {
      tags.innerHTML =
        '<span class="badge badge-primary">' + data.categoria + '</span>' +
        '<span class="badge badge-info">' + data.combustible + '</span>' +
        '<span class="badge badge-accent">' + data.condicion + '</span>' +
        '<span class="badge badge-primary">' + data.anio + ' · ' + data.variante + '</span>';
    }
    if (desc) desc.textContent = data.descripcion || '';
    if (price) price.textContent = formatSoles(data.precio);
    modal.classList.add('open');
  };

  window.closeVehicleInfoModal = function () {
    var modal = document.getElementById('vehicle-info-modal');
    if (modal) modal.classList.remove('open');
  };

  window.initWizardCatalogPicker = function (initialId) {
    var grid = document.getElementById('wizard-catalog-grid');
    var search = document.getElementById('wizard-catalog-search');
    var tabs = document.querySelectorAll('.wizard-catalog-tab');
    var err = document.getElementById('wizard-catalog-error');
    var selectedCard = document.getElementById('wizard-selected-card');
    var infoBtn = document.getElementById('wizard-vehicle-info-btn');
    var activeFilter = 'todos';
    var currentVehicle = null;

    function applyFilters() {
      if (!grid) return;
      var q = (search && search.value ? search.value : '').toLowerCase().trim();
      grid.querySelectorAll('.wizard-catalog-pick').forEach(function (btn) {
        var matchCat = activeFilter === 'todos' || btn.dataset.categoria === activeFilter;
        var matchSearch = !q || (btn.dataset.search || '').includes(q);
        btn.style.display = matchCat && matchSearch ? '' : 'none';
      });
    }

    function selectVehicle(data, btn) {
      currentVehicle = data;
      document.getElementById('marca_vehiculo').value = data.marca;
      document.getElementById('modelo_vehiculo').value = data.modelo + ' ' + data.anio;
      document.getElementById('precio_vehiculo').value = data.precio;
      document.getElementById('catalogo_id').value = data.id;
      var display = document.getElementById('precio_vehiculo_display');
      if (display) display.value = formatSoles(data.precio);
      if (selectedCard) {
        selectedCard.style.display = '';
        document.getElementById('wizard-selected-title').textContent = data.marca + ' ' + data.modelo;
        document.getElementById('wizard-selected-meta').textContent =
          data.anio + ' · ' + data.variante + ' · ' + data.categoria;
        document.getElementById('wizard-selected-price').textContent = formatSoles(data.precio);
        var imgWrap = document.getElementById('wizard-selected-image-wrap');
        if (imgWrap) {
          imgWrap.innerHTML = data.imagen_url
            ? '<img src="' + data.imagen_url + '" alt="" />'
            : '<div class="wizard-catalog-pick-placeholder">🚗</div>';
        }
      }
      grid.querySelectorAll('.wizard-catalog-pick').forEach(function (b) { b.classList.remove('selected'); });
      if (btn) btn.classList.add('selected');
      if (err) err.style.display = 'none';
    }

    window.validateWizardVehicleStep = function () {
      var id = document.getElementById('catalogo_id').value;
      var precio = document.getElementById('precio_vehiculo').value;
      if (!id || !precio || Number(precio) <= 0) {
        if (err) err.style.display = 'block';
        if (grid) grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
        return false;
      }
      if (err) err.style.display = 'none';
      return true;
    };

    if (grid) {
      grid.querySelectorAll('.wizard-catalog-pick').forEach(function (btn) {
        btn.addEventListener('click', function () {
          selectVehicle(JSON.parse(btn.dataset.vehicle), btn);
        });
      });
      if (initialId) {
        var pre = grid.querySelector('.wizard-catalog-pick[data-id="' + initialId + '"]');
        if (pre) selectVehicle(JSON.parse(pre.dataset.vehicle), pre);
      } else {
        var marcaEl = document.getElementById('marca_vehiculo');
        var modeloEl = document.getElementById('modelo_vehiculo');
        if (marcaEl && marcaEl.value && modeloEl && modeloEl.value) {
          grid.querySelectorAll('.wizard-catalog-pick').forEach(function (btn) {
            var d = JSON.parse(btn.dataset.vehicle);
            if (d.marca === marcaEl.value.trim() && modeloEl.value.indexOf(d.modelo) !== -1) {
              selectVehicle(d, btn);
            }
          });
        }
      }
    }

    if (search) search.addEventListener('input', applyFilters);
    tabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        tabs.forEach(function (t) { t.classList.remove('active'); });
        tab.classList.add('active');
        activeFilter = tab.dataset.filter;
        applyFilters();
      });
    });

    if (infoBtn) {
      infoBtn.addEventListener('click', function () {
        if (currentVehicle) openVehicleInfoModal(currentVehicle);
      });
    }

    var infoModal = document.getElementById('vehicle-info-modal');
    if (infoModal) {
      infoModal.addEventListener('click', function (e) {
        if (e.target === infoModal) closeVehicleInfoModal();
      });
    }

    applyFilters();
  };
})();
