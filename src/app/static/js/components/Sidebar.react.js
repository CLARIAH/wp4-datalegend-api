var React = require('react');
var ReactPropTypes = React.PropTypes;
var DatasetActions = require('../actions/DatasetActions');
var PillSelector = require('./PillSelector.react');



var Sidebar = React.createClass({

  // This React class only works if a list of 'options' is passed through its properties.
  propTypes: {
    options: ReactPropTypes.array.isRequired
  },

  /**
   * @return {object}
   */
  render: function() {
    return (
      <div className="col-md-2 col-sm-3 sidebar">
        <section id="variable_select_panel">
          <h4>Variables</h4>
          <PillSelector options={this.props.options} doSelect={this._onSelected}/>
        </section>
      </div>
    );
  },

  /**
   * Event handler for selections in the PillSelector
   */
  _onSelected: function(value) {
    DatasetActions.chooseVariable(value);
  }

});

module.exports = Sidebar;