import React from 'react';
import { Dialog, DialogActions, Button, DialogTitle, DialogContent, DialogContentText, } from '@material-ui/core';

import './Suggestion.css';

export default class Suggestion extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            open: false,
            name: props.suggestion.name,
            variety: props.suggestion.variety,
            description: props.suggestion.description,
        };
    }

    handleClickOpen = () => {
        this.setState({ open: true });
    }

    handleClose = () => {
        this.setState({ open: false });
    }

    render() {
        return (
            <div class="card" onClick={this.handleClickOpen}>
                <div>
                    {this.state.name} ({this.state.variety})
                </div>
                <Dialog
                    open={this.state.open}
                    onClose={this.handleClose}
                    aria-labelledby="alert-dialog-title"
                    aria-describedby="alert-dialog-description"
                >
                    <DialogTitle id="alert-dialog-title">
                        {this.state.name}
                    </DialogTitle>
                    <DialogContent>
                        <DialogContentText id="alert-dialog-description">
                            {this.state.description}
                        </DialogContentText>
                    </DialogContent>
                    <DialogActions>
                        <Button onClick={this.handleClose} autoFocus>
                            Okay
                        </Button>
                    </DialogActions>
                </Dialog>
            </div>
        );
    }
}