import React from 'react';
import './SearchBox.css'
import Suggestion from './Suggestion';

export default class SearchBox extends React.Component {
    constructor(props) {
        super(props);

        this.state = {
            suggestions: [
                {
                    name: "the coolest",
                    variety: "a variety",
                    description: "this wine tastes really good",
                },
                {
                    name: "another coolest",
                    variety: "another variety",
                    description: "this wine tastes really good",
                },
            ],
            query: '',
            endpointUrl: ""
        };
    }

    async fetchData() {

        const suggestions = fetch(this.state.endpointUrl, {

        })
        console.log(suggestions);

        this.setState({ suggestions: suggestions });
    }

    onSearch = () => {
        this.fetchData();
    }

    handleChange = (e) => {
        this.setState({ query: e.target.value });
    }

    render() {
        const items = this.state.suggestions.map((value) => {
            return <Suggestion suggestion={value} />
        })

        return (
            <div>
                <div className="SearchBox">
                    <input value={this.state.query} onChange={this.handleChange} type="textarea" />
                    <button onClick={this.onSearch}>Search</button>
                </div>
                <div>
                    {items}
                </div>
            </div>
        )
    }
}

