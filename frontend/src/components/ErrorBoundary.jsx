import { Component } from 'react';
import GenericErrorView from './GenericErrorView.jsx';

// Last line of defence for rendering bugs: a fixed message, never the
// exception text or stack.
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
    this.reset = this.reset.bind(this);
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  reset() {
    this.setState({ failed: false });
  }

  render() {
    if (this.state.failed) {
      return (
        <div className="page page--narrow">
          <GenericErrorView level={1} onRetry={this.reset} />
        </div>
      );
    }
    return this.props.children;
  }
}
